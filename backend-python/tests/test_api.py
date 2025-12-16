from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    # The root endpoint returns name, version, status, docs, redoc
    # It does NOT return "message"
    data = response.json()
    assert "name" in data
    assert "status" in data

def test_assistant_greeting():
    response = client.get("/assistant/greeting", params={"session_id": "test-session"})
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    # The greeting endpoint returns a simplified response structure, not the full MessageResponse
    # It returns session_id, message, and suggested_actions
    assert "suggested_actions" in data
    assert isinstance(data["suggested_actions"], list)

def test_assistant_message_policy():
    """Test a policy question which doesn't require LLM/DB necessarily if handled by intent"""
    payload = {
        "session_id": "test-session-002",
        "message": "What's your return policy?"
    }
    response = client.post("/assistant/message", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    # Note: Intent detection might be rule-based or LLM-based. 
    # If it's rule-based, we expect "return_policy" intent.
