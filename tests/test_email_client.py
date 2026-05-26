"""Tests for the Resend email wrapper."""
from unittest.mock import patch, MagicMock
from server import email_client


def test_send_confirmation_calls_resend_with_expected_args(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test_key")
    monkeypatch.setenv("RESEND_FROM", "test@example.com")

    mock_send = MagicMock(return_value={"id": "msg_123"})
    with patch("resend.Emails.send", mock_send):
        result = email_client.send_confirmation("alice@example.com")

    assert result == {"id": "msg_123"}
    args, _ = mock_send.call_args
    payload = args[0]
    assert payload["from"] == "test@example.com"
    assert payload["to"] == ["alice@example.com"]
    assert payload["subject"] == "You're on the list."


def test_send_confirmation_includes_body(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test_key")
    monkeypatch.setenv("RESEND_FROM", "test@example.com")

    captured = {}
    def fake_send(payload):
        captured.update(payload)
        return {"id": "msg_456"}

    with patch("resend.Emails.send", side_effect=fake_send):
        email_client.send_confirmation("bob@example.com")

    assert "html" in captured or "text" in captured
    # Must mention Promptiv somewhere
    body = (captured.get("html", "") + captured.get("text", "")).lower()
    assert "promptiv" in body


def test_send_confirmation_returns_none_on_failure(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test_key")
    monkeypatch.setenv("RESEND_FROM", "test@example.com")

    with patch("resend.Emails.send", side_effect=Exception("network error")):
        # Should swallow exception and return None — signup should not fail because email failed
        result = email_client.send_confirmation("carol@example.com")
    assert result is None
