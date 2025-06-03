from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_rewrite_endpoint():
    response = client.post("/api/rewrite", json={"prompt": "Hello GPT!"})
    assert response.status_code == 200
    data = response.json()
    assert "improved" in data
    assert data["original"] == "Hello GPT!"
