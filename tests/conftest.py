"""Shared pytest fixtures."""
import pytest


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a fresh SQLite file path for each test."""
    return str(tmp_path / "test.sqlite")


@pytest.fixture
def app(temp_db_path, monkeypatch):
    """Flask app with a fresh test database."""
    monkeypatch.setenv("DATABASE_PATH", temp_db_path)
    monkeypatch.setenv("RESEND_API_KEY", "test_key")
    monkeypatch.setenv("RESEND_FROM", "test@example.com")
    monkeypatch.setenv("SECRET_KEY", "test-secret")

    from server.app import create_app
    from server.migrations import init_schema

    app = create_app()
    app.config["TESTING"] = True

    with app.app_context():
        init_schema(temp_db_path)

    return app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def seeded_client_for_gate(client, temp_db_path):
    """Client with minimal seed so /api/go returns something."""
    import sqlite3
    conn = sqlite3.connect(temp_db_path)
    try:
        conn.execute("INSERT INTO airports VALUES ('BNA','Nashville','TN','SE',36.1,-86.7,12)")
        conn.execute("INSERT INTO destinations VALUES ('MEX','Mexico City','Mexico','MX','LA','[]',1,0,'[3,4,5]',60,2,'MXN',19.4,-99.1,NULL,3)")
        conn.execute("INSERT INTO routes VALUES ('BNA','MEX',NULL)")
        conn.execute("INSERT INTO price_snapshots (origin_iata,dest_iata,departure_date,return_date,trip_nights,total_price_usd,stops,carrier_codes,source,fetched_at) VALUES ('BNA','MEX','2026-06-01','2026-06-08',7,342,NULL,NULL,'fli','2026-05-26T07:00')")
        conn.commit()
    finally:
        conn.close()
    return client
