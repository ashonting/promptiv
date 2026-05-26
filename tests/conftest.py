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
