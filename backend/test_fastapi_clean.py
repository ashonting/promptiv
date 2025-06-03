# backend/test_fastapi_clean.py

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_rewrite_unauthorized():
    response = client.post("/api/rewrite", json={"prompt": "This is a test prompt."})
    assert response.status_code == 401  # Because no auth is passed in MVP version
