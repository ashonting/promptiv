from unittest.mock import patch


def _create(client, **over):
    body = {"email": "a@b.co", "origin": "BNA", "dest": "PLS",
            "window_start": "2026-11-01", "window_end": "2027-01-31",
            "nights": 7, "ceiling": 450}
    body.update(over)
    with patch("server.app.watch_emails.send_watch_confirm",
               return_value={"id": "m"}) as s:
        resp = client.post("/api/watch", json=body,
                           headers={"Accept": "application/json"})
    return resp, s


def test_create_watch_sends_confirm(client):
    resp, send = _create(client)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "pending"
    assert send.call_count == 1


def test_create_watch_validation_400(client):
    resp, _ = _create(client, origin="QZX")
    assert resp.status_code == 400
    assert "airport" in resp.get_json()["error"]


def test_confirm_activates(client, temp_db_path):
    _create(client)
    import sqlite3
    conn = sqlite3.connect(temp_db_path)
    token = conn.execute("SELECT manage_token FROM watches").fetchone()[0]
    r = client.get(f"/watch/confirm?token={token}")
    assert r.status_code == 200 and b"watching" in r.data.lower()
    assert conn.execute("SELECT status FROM watches").fetchone()[0] == "active"


def test_confirm_bad_token_404(client):
    assert client.get("/watch/confirm?token=nope").status_code == 404


def test_manage_page_and_actions(client, temp_db_path):
    _create(client)
    import sqlite3
    conn = sqlite3.connect(temp_db_path)
    token = conn.execute("SELECT manage_token FROM watches").fetchone()[0]
    page = client.get(f"/watch/manage?token={token}")
    assert page.status_code == 200 and b"BNA" in page.data
    r = client.post("/watch/manage", data={"token": token, "action": "pause"})
    assert r.status_code == 200
    assert conn.execute("SELECT status FROM watches").fetchone()[0] == "paused"
    r = client.post("/watch/manage", data={"token": token, "action": "resume"})
    assert conn.execute("SELECT status FROM watches").fetchone()[0] == "active"
    r = client.post("/watch/manage", data={"token": token, "action": "delete"})
    assert conn.execute("SELECT status FROM watches").fetchone()[0] == "deleted"


def test_manage_bad_token_404(client):
    assert client.get("/watch/manage?token=zzz").status_code == 404
    assert client.post("/watch/manage",
                       data={"token": "zzz", "action": "pause"}).status_code == 404
