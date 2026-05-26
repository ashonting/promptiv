"""Tests for the extended /api/healthz endpoint."""


def test_healthz_returns_db_ok(client):
    rv = client.get("/api/healthz")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["status"] == "healthy"
    assert body["db"] == "ok"


def test_healthz_reports_snapshot_count(client):
    rv = client.get("/api/healthz")
    body = rv.get_json()
    assert "snapshot_count" in body
    assert isinstance(body["snapshot_count"], int)


def test_healthz_reports_last_refresh_at(client):
    rv = client.get("/api/healthz")
    body = rv.get_json()
    # Null is valid when no refresh has happened yet
    assert "last_refresh_at" in body
