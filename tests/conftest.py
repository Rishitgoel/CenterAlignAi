import asyncio
import socket
import threading
import time
import pytest
import uvicorn
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


@pytest.fixture(scope="session", autouse=True)
def run_test_server():
    """Runs a single background Uvicorn server for the entire pytest session."""
    asyncio.run(init_db())
    server = None
    is_running = False
    try:
        with socket.create_connection(("127.0.0.1", 8000), timeout=0.5):
            is_running = True
    except OSError:
        is_running = False

    if not is_running:
        server = ServerThread()
        server.start()
        time.sleep(1.5)

    yield

    if server:
        server.stop()
