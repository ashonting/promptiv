"""Tests for /api/signup endpoint."""
from unittest.mock import patch
from server import db


def test_signup_creates_row(client):
    with patch("server.email_client.send_confirmation", return_value={"id": "msg"}):
        resp = client.post("/api/signup", json={"email": "alice@example.com"})
    assert resp.status_code == 200
    data = resp.get_json()
    assert "signup_id" in data
    assert isinstance(data["signup_id"], int)

    row = db.get_signup_by_email("alice@example.com")
    assert row is not None


def test_signup_dedup_returns_existing_id(client):
    with patch("server.email_client.send_confirmation", return_value={"id": "msg"}):
        r1 = client.post("/api/signup", json={"email": "bob@example.com"})
        r2 = client.post("/api/signup", json={"email": "bob@example.com"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.get_json()["signup_id"] == r2.get_json()["signup_id"]


def test_signup_rejects_missing_email(client):
    resp = client.post("/api/signup", json={})
    assert resp.status_code == 400


def test_signup_rejects_empty_email(client):
    resp = client.post("/api/signup", json={"email": ""})
    assert resp.status_code == 400


def test_signup_rejects_invalid_email(client):
    resp = client.post("/api/signup", json={"email": "not-an-email"})
    assert resp.status_code == 400


def test_signup_normalizes_email_case_and_whitespace(client):
    with patch("server.email_client.send_confirmation", return_value={"id": "msg"}):
        client.post("/api/signup", json={"email": "  Carol@Example.com  "})
    row = db.get_signup_by_email("carol@example.com")
    assert row is not None


def test_signup_triggers_confirmation_email(client):
    with patch("server.email_client.send_confirmation", return_value={"id": "msg"}) as mock_send:
        client.post("/api/signup", json={"email": "dave@example.com"})
    mock_send.assert_called_once_with("dave@example.com")


def test_signup_succeeds_even_if_email_fails(client):
    with patch("server.email_client.send_confirmation", return_value=None):
        resp = client.post("/api/signup", json={"email": "eve@example.com"})
    assert resp.status_code == 200
    row = db.get_signup_by_email("eve@example.com")
    assert row is not None


def test_healthz_returns_ok(client):
    resp = client.get("/api/healthz")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "signups" in data
