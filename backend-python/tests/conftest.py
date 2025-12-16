import pytest
import asyncio
from typing import Generator
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="module")
def client() -> Generator:
    """Create a TestClient instance."""
    with TestClient(app) as c:
        yield c
