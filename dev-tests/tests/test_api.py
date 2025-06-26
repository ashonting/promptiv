from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_health_check():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}

def test_llm_count():
    resp = client.get("/api/llm_count")
    assert resp.status_code == 200
    data = resp.json()
    assert "models" in data and isinstance(data["models"], list)

def test_rewrite_requires_auth_or_device():
    # No auth or device_hash → 401
    resp = client.post("/api/rewrite", json={"prompt": "Hello GPT!"})
    assert resp.status_code == 401

def test_rewrite_anonymous_device_hash():
    # provide device_hash for anonymous flow
    device = "test-device-123"
    resp = client.post(
        "/api/rewrite",
        json={"prompt": "Hello GPT!", "device_hash": device}
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["input"] == "Hello GPT!"
    assert isinstance(payload["variants"], list)
    # sanity-check one variant
    variant = payload["variants"][0]
    assert "variant_style" in variant and "prompt" in variant
