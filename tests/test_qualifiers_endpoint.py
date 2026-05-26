"""Tests for /api/qualifiers/<signup_id> endpoint."""
from unittest.mock import patch
from server import db


def _create_signup(client, email="x@example.com"):
    with patch("server.email_client.send_confirmation", return_value={"id": "msg"}):
        resp = client.post("/api/signup", json={"email": email})
    return resp.get_json()["signup_id"]


def test_qualifiers_creates_row(client):
    signup_id = _create_signup(client)
    resp = client.post(f"/api/qualifiers/{signup_id}", json={
        "budget_bucket": "mid",
        "home_airport": "BNA",
        "frustration": "everything is overwhelming"
    })
    assert resp.status_code == 200
    row = db.get_qualifiers_by_signup_id(signup_id)
    assert row["budget_bucket"] == "mid"
    assert row["home_airport"] == "BNA"


def test_qualifiers_accepts_partial(client):
    signup_id = _create_signup(client)
    resp = client.post(f"/api/qualifiers/{signup_id}", json={"budget_bucket": "low"})
    assert resp.status_code == 200
    row = db.get_qualifiers_by_signup_id(signup_id)
    assert row["budget_bucket"] == "low"
    assert row["home_airport"] is None


def test_qualifiers_returns_404_for_unknown_signup(client):
    resp = client.post("/api/qualifiers/99999", json={"budget_bucket": "mid"})
    assert resp.status_code == 404


def test_qualifiers_rejects_bad_bucket(client):
    signup_id = _create_signup(client)
    resp = client.post(f"/api/qualifiers/{signup_id}", json={"budget_bucket": "huge"})
    assert resp.status_code == 400


def test_qualifiers_truncates_long_frustration(client):
    signup_id = _create_signup(client)
    long_text = "x" * 1000
    resp = client.post(f"/api/qualifiers/{signup_id}", json={"frustration": long_text})
    assert resp.status_code == 200
    row = db.get_qualifiers_by_signup_id(signup_id)
    assert len(row["frustration"]) == 500


def test_qualifiers_upsert_overwrites(client):
    signup_id = _create_signup(client)
    client.post(f"/api/qualifiers/{signup_id}", json={"budget_bucket": "low"})
    client.post(f"/api/qualifiers/{signup_id}", json={"budget_bucket": "stretch", "home_airport": "LAX"})
    row = db.get_qualifiers_by_signup_id(signup_id)
    assert row["budget_bucket"] == "stretch"
    assert row["home_airport"] == "LAX"
