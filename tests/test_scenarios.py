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
