import asyncio
import threading
import time
import pytest
import uvicorn
import aiosqlite
from config import settings
from agent.core import Agent
from agent.models import AgentState
from mock_erp.app import app
from mock_erp.database import init_db


def teardown_module():

    # Re-seed sample demonstration invoices so Web Portal is populated after test runs
    async def _restore_demo_invoices():
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        samples = [
            ("Acme Corp", "INV-2024-001", 1500.00, "USD", "2026-10-15", "approved", "[]", "Consulting Services - December", now),
            ("Globex Corporation", "GLX-7892", 3250.75, "USD", "2026-10-30", "verified", "[]", "Q3 Cloud Infrastructure Support", now),
        ]
        async with aiosqlite.connect(settings.database_path) as conn:
            for inv in samples:
                try:
                    await conn.execute(
                        """
                        INSERT INTO invoices (vendor_name, invoice_number, amount, currency, due_date, status, line_items_json, notes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        inv,
                    )
                except Exception:
                    pass
            await conn.commit()

    asyncio.run(_restore_demo_invoices())


def setup_function():
    # Clear invoices before each test to guarantee fresh, non-conflicting state
    async def _clear():
        async with aiosqlite.connect(settings.database_path) as conn:
            await conn.execute("DELETE FROM invoices")
            await conn.commit()
    asyncio.run(_clear())


def test_scenario_1_happy_path():
    async def _run():
        agent = Agent(interactive=False)
        task = "Process the invoice from demo/invoices/invoice_globex_002.json into our ERP system."
        log = await agent.run(task)

        assert log.final_state == AgentState.COMPLETED
        assert "Globex Corporation" in log.summary
        assert "evidence" in log.model_dump()
        assert "erp_record" in log.evidence
        assert log.evidence["erp_record"]["invoice_number"] == "GLX-7892"
        assert log.evidence["erp_record"]["amount"] == 3250.75

    asyncio.run(_run())


def test_scenario_2_error_recovery():
    async def _run():
        agent = Agent(interactive=False)
        task = "Process the invoice from demo/invoices/invoice_malformed_003.json and record it into our ERP system."
        log = await agent.run(task)

        assert log.final_state == AgentState.COMPLETED
        assert "Initech" in log.summary
        assert "erp_record" in log.evidence
        assert log.evidence["erp_record"]["vendor_name"] == "Initech"
        assert log.evidence["erp_record"]["amount"] == 2100.5

    asyncio.run(_run())


def test_scenario_3_human_escalation_detection():
    async def _run():
        agent = Agent(interactive=False)
        task = "Process the high-value vendor invoice from demo/invoices/invoice_highvalue_004.json into our ERP system."
        log = await agent.run(task)

        assert log.final_state == AgentState.COMPLETED
        assert "Stark Industries" in log.summary
        assert log.evidence["erp_record"]["amount"] == 75000.0

    asyncio.run(_run())


def test_scenario_4_browser_ui_automation():
    async def _run():
        agent = Agent(interactive=False)
        task = "Open the company web portal in the browser, extract the invoice details from demo/invoices/invoice_acme_001.json, submit the invoice form via the UI modal, and verify completion."
        log = await agent.run(task)

        assert log.final_state == AgentState.COMPLETED
        assert "Acme Corp" in log.summary
        assert "evidence" in log.model_dump()
        assert "screenshot_path" in log.evidence
        assert "erp_record" in log.evidence
        assert log.evidence["erp_record"]["vendor_name"] == "Acme Corp"
        assert log.evidence["erp_record"]["amount"] == 1500.0

    asyncio.run(_run())


def test_scenario_5_multimodal_document_ingestion():
    async def _run():
        agent = Agent(interactive=False)
        task = "Extract invoice information from vendor email demo/invoices/invoice_vendor_email_006.eml, enter it into our ERP system, and verify completion."
        log = await agent.run(task)

        assert log.final_state == AgentState.COMPLETED
        assert "Cyberdyne Systems" in log.summary
        assert "evidence" in log.model_dump()
        assert "erp_record" in log.evidence
        assert log.evidence["erp_record"]["amount"] == 5400.0

    asyncio.run(_run())


def test_scenario_6_dynamic_openapi_synthesis():
    from tools.openapi_loader import OpenAPILoader
    from mock_erp.app import app

    spec = app.openapi()
    dynamic_tools = OpenAPILoader.load_from_spec(spec, base_url="http://127.0.0.1:8000")
    assert len(dynamic_tools) >= 5

    # Register dynamic tools into agent registry
    agent = Agent(interactive=False)
    for tool in dynamic_tools:
        agent.registry.register(tool)

    assert agent.registry.get("api_health_check_health_get") is not None
    assert agent.registry.get("api_list_invoices_invoices_get") is not None


def test_scenario_7_cryptographic_audit_ledger(tmp_path):
    from security.audit_ledger import CryptographicAuditLedger
    import json

    test_ledger_file = tmp_path / "test_ledger.jsonl"
    ledger = CryptographicAuditLedger(ledger_file=str(test_ledger_file))

    b1 = ledger.record_event("task_001", "STATE_TRANSITION", {"state": "PLANNING"})
    b2 = ledger.record_event("task_001", "TOOL_EXECUTION", {"tool": "read_file", "success": True})
    b3 = ledger.record_event("task_001", "VERIFICATION_RESULT", {"status": "PASSED"})

    assert b1.index == 1
    assert b2.index == 2
    assert b3.previous_hash == b2.block_hash

    # Validate integrity
    verification = ledger.verify_ledger_integrity()
    assert verification["valid"] is True
    assert verification["blocks_verified"] == 3

    # Tamper with block 2
    lines = test_ledger_file.read_text(encoding="utf-8").strip().split("\n")
    corrupt_block = json.loads(lines[1])
    corrupt_block["payload"]["tool"] = "malicious_injected_tool"
    lines[1] = json.dumps(corrupt_block)
    test_ledger_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    tampered_check = ledger.verify_ledger_integrity()
    assert tampered_check["valid"] is False
    assert tampered_check["broken_at_index"] == 2


def test_scenario_8_credential_vault_redaction():
    from security.credential_vault import CredentialVault

    vault = CredentialVault()
    vault.store_secret("ERP_API_KEY", "super_secret_token_12345")

    raw_text = "Connecting to ERP using super_secret_token_12345 with Bearer abcdef1234567890xyz"
    clean_text = vault.redact_text(raw_text)
    assert "super_secret_token_12345" not in clean_text
    assert "[REDACTED" in clean_text

    raw_dict = {
        "user": "admin",
        "api_key": "raw_injected_api_key_value",
        "nested": {"password": "admin_password_999"},
    }
    clean_dict = vault.redact_dict(raw_dict)
    assert clean_dict["api_key"] == "[REDACTED_SECRET]"
    assert clean_dict["nested"]["password"] == "[REDACTED_SECRET]"


def test_scenario_9_worker_service_job_queue(tmp_path):
    from infrastructure.worker import WorkerService

    worker = WorkerService(job_store_dir=str(tmp_path / "jobs"))
    job_id = worker.submit_task("Process invoice from Acme")

    job = worker.get_job(job_id)
    assert job is not None
    assert job.status == "PENDING"
    assert "Acme" in job.task


def test_scenario_10_in_app_dispatch_and_streaming():
    from httpx import ASGITransport, AsyncClient

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            dispatch_resp = await ac.post(
                "/api/agent/dispatch",
                json={"task": "Process invoice demo/invoices/invoice_globex_002.json into the ERP system."},
            )
            assert dispatch_resp.status_code == 200
            task_id = dispatch_resp.json()["task_id"]

            for _ in range(30):
                await asyncio.sleep(0.5)
                status_resp = await ac.get(f"/api/agent/tasks/{task_id}")
                task_info = status_resp.json()
                if task_info["status"] in ["COMPLETED", "FAILED"]:
                    break

            assert task_info["status"] == "COMPLETED"
            event_types = [ev.get("type") for ev in task_info["events"]]
            assert "STATE_CHANGE" in event_types
            assert "TASK_COMPLETED" in event_types

    asyncio.run(_run())


def test_scenario_11_dynamic_pdf_upload_and_ingestion():
    import io
    from httpx import ASGITransport, AsyncClient

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            # 1. Dispatch prompt without file
            dispatch_resp = await ac.post(
                "/api/agent/dispatch",
                json={"task": "Add this PDF invoice into our ERP system."},
            )
            assert dispatch_resp.status_code == 200
            task_id = dispatch_resp.json()["task_id"]

            # Wait for PENDING_INPUT
            for _ in range(20):
                await asyncio.sleep(0.3)
                status_resp = await ac.get(f"/api/agent/tasks/{task_id}")
                task_info = status_resp.json()
                if task_info["status"] == "PENDING_INPUT":
                    break

            assert task_info["status"] == "PENDING_INPUT"

            # 2. Upload file via /api/agent/upload
            with open("demo/invoices/invoice_globex_002.json", "rb") as f:
                files = {"file": ("invoice_globex_002.json", f.read(), "application/json")}
            upload_resp = await ac.post("/api/agent/upload", files=files)
            assert upload_resp.status_code == 200
            uploaded_path = upload_resp.json()["file_path"]

            # 3. Provide uploaded file path
            input_resp = await ac.post(
                f"/api/agent/tasks/{task_id}/input",
                json={"file_path": uploaded_path},
            )
            assert input_resp.status_code == 200

            # 4. Wait for completion
            for _ in range(30):
                await asyncio.sleep(0.5)
                status_resp = await ac.get(f"/api/agent/tasks/{task_id}")
                task_info = status_resp.json()
                if task_info["status"] in ["COMPLETED", "FAILED"]:
                    break

            assert task_info["status"] == "COMPLETED"

            # 5. Check database has Globex invoice
            inv_resp = await ac.get("/invoices")
            vendors = [inv["vendor_name"] for inv in inv_resp.json()]
            assert "Globex Corporation" in vendors

    asyncio.run(_run())


def test_scenario_12_in_app_hitl_approval_flow():
    from httpx import ASGITransport, AsyncClient

    async def _run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            dispatch_resp = await ac.post(
                "/api/agent/dispatch",
                json={"task": "Process invoice demo/invoices/invoice_highvalue_004.json into our ERP system."},
            )
            assert dispatch_resp.status_code == 200
            task_id = dispatch_resp.json()["task_id"]

            # Wait for PENDING_APPROVAL
            for _ in range(30):
                await asyncio.sleep(0.5)
                status_resp = await ac.get(f"/api/agent/tasks/{task_id}")
                task_info = status_resp.json()
                if task_info["status"] == "PENDING_APPROVAL":
                    break

            assert task_info["status"] == "PENDING_APPROVAL"

            # Approve via API
            approve_resp = await ac.post(f"/api/agent/tasks/{task_id}/approve")
            assert approve_resp.status_code == 200

            # Wait for completion
            for _ in range(30):
                await asyncio.sleep(0.5)
                status_resp = await ac.get(f"/api/agent/tasks/{task_id}")
                task_info = status_resp.json()
                if task_info["status"] in ["COMPLETED", "FAILED"]:
                    break

            assert task_info["status"] == "COMPLETED"

    asyncio.run(_run())


