from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_rewrite_no_credentials():
    # Neither logged in nor device_hash → HTTP 401
    response = client.post("/api/rewrite", json={"prompt": "This is a test prompt."})
    assert response.status_code == 401

def test_rewrite_with_device_hash():
    # Anonymous trial via device_hash
    device = "anon-device-xyz"
    response = client.post(
        "/api/rewrite",
        json={"prompt": "Test prompt", "device_hash": device}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["input"] == "Test prompt"
    assert isinstance(body["variants"], list)
    # check that clarity/complexity show up
    for v in body["variants"]:
        assert "clarity" in v and "complexity" in v
