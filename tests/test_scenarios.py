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


class ServerThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
        self.server = uvicorn.Server(config)

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True


_server_thread = None


def setup_module():
    global _server_thread
    asyncio.run(init_db())
    _server_thread = ServerThread()
    _server_thread.start()
    time.sleep(1.5)  # Wait for uvicorn to bind


def teardown_module():
    global _server_thread
    if _server_thread:
        _server_thread.stop()


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

