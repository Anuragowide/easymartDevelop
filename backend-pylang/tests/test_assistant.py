from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings


def test_assistant_message_smoke():
    settings = get_settings()
    settings.TEST_MODE = True

    client = TestClient(app)
    payload = {"session_id": "test-session", "message": "hello"}
    resp = client.post("/assistant/message", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"]
    assert body["session_id"] == "test-session"
