from fastapi.testclient import TestClient
from app.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health/")
    assert resp.status_code == 200
    body = resp.json()
    assert body.get("status") in ["healthy", "degraded", "unhealthy"]
