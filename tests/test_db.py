"""Tests for db access layer."""
import pytest
from server.migrations import init_schema
from server import db


@pytest.fixture
def initialized_db(temp_db_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", temp_db_path)
    init_schema(temp_db_path)
    return temp_db_path


def test_insert_signup_returns_id(initialized_db):
    signup_id = db.insert_signup("a@example.com", ip_hash="abc", referrer="https://x.com")
    assert signup_id is not None
    assert signup_id >= 1


def test_insert_signup_dedup_returns_existing_id(initialized_db):
    first_id = db.insert_signup("a@example.com", ip_hash="abc")
    second_id = db.insert_signup("a@example.com", ip_hash="def")
    assert first_id == second_id


def test_get_signup_by_email_returns_row(initialized_db):
    db.insert_signup("a@example.com", ip_hash="abc")
    row = db.get_signup_by_email("a@example.com")
    assert row is not None
    assert row["email"] == "a@example.com"


def test_get_signup_by_email_missing_returns_none(initialized_db):
    assert db.get_signup_by_email("nobody@example.com") is None


def test_upsert_qualifiers_creates_row(initialized_db):
    signup_id = db.insert_signup("a@example.com")
    db.upsert_qualifiers(signup_id, budget_bucket="mid", home_airport="BNA", frustration="too many tabs")
    row = db.get_qualifiers_by_signup_id(signup_id)
    assert row["budget_bucket"] == "mid"
    assert row["home_airport"] == "BNA"
    assert row["frustration"] == "too many tabs"


def test_upsert_qualifiers_updates_existing(initialized_db):
    signup_id = db.insert_signup("a@example.com")
    db.upsert_qualifiers(signup_id, budget_bucket="low")
    db.upsert_qualifiers(signup_id, budget_bucket="stretch", home_airport="LAX")
    row = db.get_qualifiers_by_signup_id(signup_id)
    assert row["budget_bucket"] == "stretch"
    assert row["home_airport"] == "LAX"


def test_upsert_qualifiers_rejects_bad_bucket(initialized_db):
    signup_id = db.insert_signup("a@example.com")
    with pytest.raises(ValueError):
        db.upsert_qualifiers(signup_id, budget_bucket="invalid")


def test_count_signups(initialized_db):
    assert db.count_signups() == 0
    db.insert_signup("a@example.com")
    db.insert_signup("b@example.com")
    assert db.count_signups() == 2
