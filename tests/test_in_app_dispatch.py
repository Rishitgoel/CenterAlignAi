import asyncio
import io
import json
import pytest
from httpx import ASGITransport, AsyncClient
import aiosqlite

from config import settings
from mock_erp.app import app
from mock_erp.database import init_db


@pytest.fixture(autouse=True)
async def fresh_db():
    await init_db()
    async with aiosqlite.connect(settings.database_path) as conn:
        await conn.execute("DELETE FROM invoices")
        await conn.commit()
    yield
    # Cleanup after test
    async with aiosqlite.connect(settings.database_path) as conn:
        await conn.execute("DELETE FROM invoices")
        await conn.commit()


@pytest.mark.anyio
async def test_dispatch_and_polling():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        dispatch_resp = await ac.post(
            "/api/agent/dispatch",
            json={"task": "Process invoice demo/invoices/invoice_globex_002.json into the ERP system."},
        )
        assert dispatch_resp.status_code == 200
        data = dispatch_resp.json()
        task_id = data["task_id"]
        assert data["status"] == "STARTED"

        # Poll status until task reaches terminal state
        terminal_status = None
        for _ in range(30):
            await asyncio.sleep(0.5)
            status_resp = await ac.get(f"/api/agent/tasks/{task_id}")
            assert status_resp.status_code == 200
            task_info = status_resp.json()
            if task_info["status"] in ["COMPLETED", "FAILED"]:
                terminal_status = task_info["status"]
                break

        assert terminal_status == "COMPLETED"
        assert len(task_info["events"]) > 0
        event_types = [ev.get("type") for ev in task_info["events"]]
        assert "TASK_STARTED" in event_types
        assert "STATE_CHANGE" in event_types
        assert "PLAN_CREATED" in event_types
        assert "TASK_COMPLETED" in event_types


@pytest.mark.anyio
async def test_hitl_approval_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        dispatch_resp = await ac.post(
            "/api/agent/dispatch",
            json={"task": "Process invoice demo/invoices/invoice_highvalue_004.json into our ERP system."},
        )
        assert dispatch_resp.status_code == 200
        task_id = dispatch_resp.json()["task_id"]

        # Wait until task transitions to PENDING_APPROVAL
        is_pending = False
        for _ in range(30):
            await asyncio.sleep(0.5)
            status_resp = await ac.get(f"/api/agent/tasks/{task_id}")
            task_info = status_resp.json()
            if task_info["status"] == "PENDING_APPROVAL":
                is_pending = True
                break

        assert is_pending is True

        # Call approve endpoint
        approve_resp = await ac.post(f"/api/agent/tasks/{task_id}/approve")
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"

        # Wait for task to resume and complete
        terminal_status = None
        for _ in range(30):
            await asyncio.sleep(0.5)
            status_resp = await ac.get(f"/api/agent/tasks/{task_id}")
            task_info = status_resp.json()
            if task_info["status"] in ["COMPLETED", "FAILED"]:
                terminal_status = task_info["status"]
                break

        assert terminal_status == "COMPLETED"


@pytest.mark.anyio
async def test_upload_and_dynamic_intake_flow():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Test File Upload endpoint
        fake_pdf = b"%PDF-1.4 test invoice content"
        files = {"file": ("test_invoice.pdf", io.BytesIO(fake_pdf), "application/pdf")}
        upload_resp = await ac.post("/api/agent/upload", files=files)
        assert upload_resp.status_code == 200
        upload_data = upload_resp.json()
        assert upload_data["status"] == "uploaded"
        assert "file_path" in upload_data
        uploaded_path = upload_data["file_path"]

        # 2. Test Dynamic Intake Prompting
        dispatch_resp = await ac.post(
            "/api/agent/dispatch",
            json={"task": "Add this PDF invoice into our ERP system."},
        )
        assert dispatch_resp.status_code == 200
        task_id = dispatch_resp.json()["task_id"]

        # Wait until task asks for input
        is_waiting_input = False
        for _ in range(20):
            await asyncio.sleep(0.3)
            status_resp = await ac.get(f"/api/agent/tasks/{task_id}")
            task_info = status_resp.json()
            if task_info["status"] == "PENDING_INPUT":
                is_waiting_input = True
                break

        assert is_waiting_input is True

        # Provide a valid demo invoice path to resume execution
        input_resp = await ac.post(
            f"/api/agent/tasks/{task_id}/input",
            json={"file_path": "demo/invoices/invoice_globex_002.json"},
        )
        assert input_resp.status_code == 200
        assert input_resp.json()["status"] == "input_received"

        # Verify task resumes and reaches COMPLETED
        terminal_status = None
        for _ in range(30):
            await asyncio.sleep(0.5)
            status_resp = await ac.get(f"/api/agent/tasks/{task_id}")
            task_info = status_resp.json()
            if task_info["status"] in ["COMPLETED", "FAILED"]:
                terminal_status = task_info["status"]
                break

        assert terminal_status == "COMPLETED"


@pytest.mark.anyio
async def test_sse_event_stream():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        dispatch_resp = await ac.post(
            "/api/agent/dispatch",
            json={"task": "Process invoice demo/invoices/invoice_globex_002.json into the ERP system."},
        )
        assert dispatch_resp.status_code == 200
        task_id = dispatch_resp.json()["task_id"]

        received_types = []
        async with ac.stream("GET", f"/api/agent/tasks/{task_id}/events") as stream:
            assert stream.status_code == 200
            async for line in stream.aiter_lines():
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    t = payload.get("type")
                    if t:
                        received_types.append(t)
                    if t in ["TASK_COMPLETED", "TASK_FAILED"]:
                        break

        assert "TASK_STARTED" in received_types
        assert "TASK_COMPLETED" in received_types

