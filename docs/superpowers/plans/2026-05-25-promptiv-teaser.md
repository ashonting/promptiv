# Promptiv Teaser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy the Promptiv teaser at promptiv.io. A single static page with rotating example trip cards, an email signup form, and a post-submit qualifier capture. All data lands in SQLite via a small Flask API. Confirmation email via Resend.

**Architecture:** Static HTML + CSS + vanilla JS (with GSAP) served by Flask. Flask also exposes `/api/signup` and `/api/qualifiers/<id>`. SQLite for persistence. Resend for confirmation email. nginx in front in production for asset caching. Everything runs on Promptiv-main.

**Tech Stack:** Python 3.11+, Flask, SQLite (stdlib), Resend Python SDK, pytest, Playwright (for E2E), GSAP 3.x, General Sans font (self-hosted), nginx, systemd.

**Spec:** `~/dashaway/docs/superpowers/specs/2026-05-25-promptiv-teaser-design.md`

---

## File Structure

```
~/dashaway/
├── PRODUCT-BRIEF.md                              # existing
├── README.md                                      # NEW — short setup notes
├── .gitignore                                     # existing
├── .env.example                                   # NEW — env var template
├── docs/superpowers/
│   ├── specs/2026-05-25-promptiv-teaser-design.md  # existing
│   └── plans/2026-05-25-promptiv-teaser.md         # this file
├── server/                                        # NEW — Flask backend
│   ├── __init__.py
│   ├── app.py                                     # Flask app + routes
│   ├── db.py                                      # SQLite connection + queries
│   ├── email_client.py                            # Resend wrapper
│   ├── migrations.py                              # schema setup
│   └── requirements.txt
├── public/                                        # NEW — static assets
│   ├── index.html                                 # the teaser
│   ├── privacy.html                               # stub
│   ├── terms.html                                 # stub
│   ├── styles.css
│   ├── app.js                                     # rotation + form behavior
│   └── fonts/                                     # self-hosted General Sans
│       ├── GeneralSans-Regular.woff2
│       ├── GeneralSans-Medium.woff2
│       ├── GeneralSans-Semibold.woff2
│       └── GeneralSans-RegularItalic.woff2
├── tests/                                         # NEW
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_db.py
│   ├── test_email_client.py
│   ├── test_signup_endpoint.py
│   ├── test_qualifiers_endpoint.py
│   └── e2e/
│       └── test_teaser_flow.py                    # Playwright
└── deploy/                                        # NEW
    ├── nginx-promptiv.conf
    ├── promptiv.service
    └── DEPLOY.md                                  # runbook
```

**Boundaries:**
- `server/db.py` is the only module that touches SQLite directly. `app.py` calls into it.
- `server/email_client.py` is the only module that talks to Resend. `app.py` calls into it.
- `public/app.js` is the only client-side JS. It calls the Flask API.
- `migrations.py` runs on startup if schema is missing; idempotent.

---

## Task 1: Scaffold project structure

**Files:**
- Create: `~/dashaway/server/__init__.py` (empty)
- Create: `~/dashaway/server/requirements.txt`
- Create: `~/dashaway/.env.example`
- Create: `~/dashaway/public/` (directory)
- Create: `~/dashaway/public/fonts/` (directory)
- Create: `~/dashaway/tests/__init__.py` (empty)
- Create: `~/dashaway/tests/conftest.py`
- Create: `~/dashaway/deploy/` (directory)
- Create: `~/dashaway/README.md`

- [ ] **Step 1: Create directory structure**

```bash
cd ~/dashaway
mkdir -p server public/fonts tests/e2e deploy
touch server/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `server/requirements.txt`**

```
Flask==3.0.3
resend==2.5.1
pytest==8.3.4
pytest-flask==1.3.0
playwright==1.50.0
python-dotenv==1.0.1
```

- [ ] **Step 3: Write `.env.example`**

```
# Resend
RESEND_API_KEY=re_replace_me
RESEND_FROM=team@mail.distillworks.com
RESEND_REPLY_TO=adam@distillworks.com

# Flask
FLASK_APP=server.app
FLASK_ENV=development
SECRET_KEY=change-me-to-a-real-random-string

# Database
DATABASE_PATH=/var/lib/promptiv/teaser.sqlite

# In dev, override DATABASE_PATH to a local file:
# DATABASE_PATH=./teaser.dev.sqlite
```

- [ ] **Step 4: Write `tests/conftest.py`**

```python
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
```

- [ ] **Step 5: Write `README.md`**

```markdown
# Promptiv

Idea-stage trip discovery product. This repo currently contains:
- `PRODUCT-BRIEF.md` — product concept
- `docs/superpowers/specs/` — design specs
- `docs/superpowers/plans/` — implementation plans
- `server/` — Flask backend
- `public/` — static teaser site
- `tests/` — pytest + Playwright
- `deploy/` — production deployment artifacts

## Local development

```bash
# Install deps (use a venv)
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt

# Copy env template
cp .env.example .env
# Edit .env, point DATABASE_PATH to a local file

# Run Flask (do this in a separate terminal — long-running)
export $(grep -v '^#' .env | xargs)
flask run --port 5000

# Open http://localhost:5000
```

## Tests

```bash
pytest tests/ -v
```

## Deploy

See `deploy/DEPLOY.md`.
```

- [ ] **Step 6: Verify structure**

Run: `find ~/dashaway -maxdepth 3 -type d ! -path '*/\.*' | sort`

Expected output includes: `~/dashaway/server`, `~/dashaway/public`, `~/dashaway/tests`, `~/dashaway/deploy`, `~/dashaway/docs/superpowers/{plans,specs}`.

- [ ] **Step 7: Commit**

```bash
cd ~/dashaway
git add server/ tests/ deploy/ public/ .env.example README.md
git commit -m "feat: scaffold project structure for teaser implementation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 2: SQLite schema and migrations

**Files:**
- Create: `~/dashaway/server/migrations.py`
- Create: `~/dashaway/tests/test_migrations.py`

- [ ] **Step 1: Write the failing test**

Create `~/dashaway/tests/test_migrations.py`:

```python
"""Tests for schema initialization."""
import sqlite3
from server.migrations import init_schema


def test_init_schema_creates_signups_table(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signups';")
    assert cur.fetchone() is not None
    conn.close()


def test_init_schema_creates_qualifiers_table(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='qualifiers';")
    assert cur.fetchone() is not None
    conn.close()


def test_signups_table_has_required_columns(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    cur = conn.execute("PRAGMA table_info(signups);")
    cols = {row[1] for row in cur.fetchall()}
    assert {"id", "email", "created_at", "ip_hash", "referrer"} <= cols
    conn.close()


def test_qualifiers_table_has_required_columns(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    cur = conn.execute("PRAGMA table_info(qualifiers);")
    cols = {row[1] for row in cur.fetchall()}
    assert {"id", "signup_id", "budget_bucket", "home_airport", "frustration", "created_at"} <= cols
    conn.close()


def test_init_schema_is_idempotent(temp_db_path):
    init_schema(temp_db_path)
    init_schema(temp_db_path)  # Running twice should not error
    conn = sqlite3.connect(temp_db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
    table_count = len([r for r in cur.fetchall() if not r[0].startswith("sqlite_")])
    assert table_count >= 2
    conn.close()


def test_email_uniqueness_enforced(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    conn.execute("INSERT INTO signups (email, created_at, ip_hash) VALUES (?, ?, ?)",
                 ("a@example.com", "2026-05-25T00:00:00", "hash1"))
    conn.commit()
    try:
        conn.execute("INSERT INTO signups (email, created_at, ip_hash) VALUES (?, ?, ?)",
                     ("a@example.com", "2026-05-25T00:01:00", "hash2"))
        conn.commit()
        assert False, "Expected IntegrityError on duplicate email"
    except sqlite3.IntegrityError:
        pass
    conn.close()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd ~/dashaway
source .venv/bin/activate  # if not already active
pytest tests/test_migrations.py -v
```

Expected: all tests FAIL with `ModuleNotFoundError: No module named 'server.migrations'`.

- [ ] **Step 3: Write minimal implementation**

Create `~/dashaway/server/migrations.py`:

```python
"""Schema initialization for the Promptiv teaser database."""
import os
import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS signups (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT NOT NULL UNIQUE,
    created_at  TEXT NOT NULL,
    ip_hash     TEXT,
    referrer    TEXT
);

CREATE TABLE IF NOT EXISTS qualifiers (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    signup_id              INTEGER NOT NULL REFERENCES signups(id) ON DELETE CASCADE,
    budget_bucket          TEXT CHECK(budget_bucket IN ('low', 'mid', 'stretch')),
    home_airport           TEXT,
    frustration            TEXT,
    created_at             TEXT NOT NULL,
    UNIQUE(signup_id)
);

CREATE INDEX IF NOT EXISTS idx_signups_email ON signups(email);
CREATE INDEX IF NOT EXISTS idx_qualifiers_signup_id ON qualifiers(signup_id);
"""


def init_schema(db_path: str) -> None:
    """Ensure schema exists at db_path. Idempotent — safe to run repeatedly."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_migrations.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server/migrations.py tests/test_migrations.py
git commit -m "feat(db): SQLite schema for signups and qualifiers

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 3: Database access layer

**Files:**
- Create: `~/dashaway/server/db.py`
- Create: `~/dashaway/tests/test_db.py`

- [ ] **Step 1: Write the failing test**

Create `~/dashaway/tests/test_db.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_db.py -v
```

Expected: tests FAIL with `ImportError` or `AttributeError` on `db.insert_signup`.

- [ ] **Step 3: Write minimal implementation**

Create `~/dashaway/server/db.py`:

```python
"""SQLite access layer for Promptiv teaser."""
import os
import sqlite3
from datetime import datetime, timezone


VALID_BUDGET_BUCKETS = {"low", "mid", "stretch"}


def _connect():
    db_path = os.environ.get("DATABASE_PATH")
    if not db_path:
        raise RuntimeError("DATABASE_PATH not set")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def insert_signup(email: str, ip_hash: str = None, referrer: str = None) -> int:
    """Insert a signup. If email exists, return the existing row's id (dedup)."""
    conn = _connect()
    try:
        cur = conn.execute("SELECT id FROM signups WHERE email = ?", (email,))
        existing = cur.fetchone()
        if existing:
            return existing["id"]

        cur = conn.execute(
            "INSERT INTO signups (email, created_at, ip_hash, referrer) VALUES (?, ?, ?, ?)",
            (email, _now(), ip_hash, referrer),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


def get_signup_by_email(email: str):
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM signups WHERE email = ?", (email,))
        return cur.fetchone()
    finally:
        conn.close()


def get_signup_by_id(signup_id: int):
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM signups WHERE id = ?", (signup_id,))
        return cur.fetchone()
    finally:
        conn.close()


def upsert_qualifiers(signup_id: int, budget_bucket: str = None,
                     home_airport: str = None, frustration: str = None):
    """Insert or update qualifier row for a signup. Validates budget_bucket."""
    if budget_bucket is not None and budget_bucket not in VALID_BUDGET_BUCKETS:
        raise ValueError(f"budget_bucket must be one of {VALID_BUDGET_BUCKETS}, got {budget_bucket}")

    conn = _connect()
    try:
        existing = conn.execute(
            "SELECT id FROM qualifiers WHERE signup_id = ?", (signup_id,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE qualifiers
                   SET budget_bucket = COALESCE(?, budget_bucket),
                       home_airport = COALESCE(?, home_airport),
                       frustration = COALESCE(?, frustration)
                   WHERE signup_id = ?""",
                (budget_bucket, home_airport, frustration, signup_id),
            )
        else:
            conn.execute(
                """INSERT INTO qualifiers
                   (signup_id, budget_bucket, home_airport, frustration, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (signup_id, budget_bucket, home_airport, frustration, _now()),
            )
        conn.commit()
    finally:
        conn.close()


def get_qualifiers_by_signup_id(signup_id: int):
    conn = _connect()
    try:
        cur = conn.execute("SELECT * FROM qualifiers WHERE signup_id = ?", (signup_id,))
        return cur.fetchone()
    finally:
        conn.close()


def count_signups() -> int:
    conn = _connect()
    try:
        return conn.execute("SELECT COUNT(*) FROM signups").fetchone()[0]
    finally:
        conn.close()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_db.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server/db.py tests/test_db.py
git commit -m "feat(db): signup and qualifier access functions with dedup

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Resend email client wrapper

**Files:**
- Create: `~/dashaway/server/email_client.py`
- Create: `~/dashaway/tests/test_email_client.py`

- [ ] **Step 1: Write the failing test**

Create `~/dashaway/tests/test_email_client.py`:

```python
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
    args, kwargs = mock_send.call_args
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_email_client.py -v
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

Create `~/dashaway/server/email_client.py`:

```python
"""Resend email wrapper for Promptiv teaser confirmations."""
import logging
import os
import resend


logger = logging.getLogger(__name__)


CONFIRMATION_HTML = """\
<p>You're on the list.</p>
<p>We're building Promptiv now. When we have something to show you, you'll be among the first to see it.</p>
<p>— The Promptiv team</p>
"""

CONFIRMATION_TEXT = """\
You're on the list.

We're building Promptiv now. When we have something to show you, you'll be among the first to see it.

— The Promptiv team
"""


def send_confirmation(email: str):
    """Send the post-signup confirmation. Returns Resend response on success, None on failure.

    Failures are logged but do not raise — a transient email failure must not block signup.
    """
    api_key = os.environ.get("RESEND_API_KEY")
    sender = os.environ.get("RESEND_FROM")
    if not api_key or not sender:
        logger.error("RESEND_API_KEY or RESEND_FROM not set; skipping email")
        return None

    resend.api_key = api_key
    payload = {
        "from": sender,
        "to": [email],
        "subject": "You're on the list.",
        "html": CONFIRMATION_HTML,
        "text": CONFIRMATION_TEXT,
    }
    reply_to = os.environ.get("RESEND_REPLY_TO")
    if reply_to:
        payload["reply_to"] = [reply_to]

    try:
        return resend.Emails.send(payload)
    except Exception as e:
        logger.exception("Resend send failed: %s", e)
        return None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_email_client.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server/email_client.py tests/test_email_client.py
git commit -m "feat(email): Resend confirmation wrapper, failures are non-fatal

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Flask app entry + /api/signup endpoint

**Files:**
- Create: `~/dashaway/server/app.py`
- Create: `~/dashaway/tests/test_signup_endpoint.py`

- [ ] **Step 1: Write the failing test**

Create `~/dashaway/tests/test_signup_endpoint.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_signup_endpoint.py -v
```

Expected: FAIL — `server.app` doesn't exist yet.

- [ ] **Step 3: Write minimal implementation**

Create `~/dashaway/server/app.py`:

```python
"""Promptiv teaser Flask app."""
import hashlib
import os
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from server import db, email_client
from server.migrations import init_schema


# RFC 5322 email — simplified pragmatic match
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _hash_ip(ip: str) -> str:
    if not ip:
        return None
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()


def create_app() -> Flask:
    public_dir = Path(__file__).resolve().parent.parent / "public"
    app = Flask(__name__, static_folder=str(public_dir), static_url_path="")

    db_path = os.environ.get("DATABASE_PATH")
    if db_path:
        init_schema(db_path)

    @app.route("/")
    def index():
        return send_from_directory(str(public_dir), "index.html")

    @app.route("/privacy")
    def privacy():
        return send_from_directory(str(public_dir), "privacy.html")

    @app.route("/terms")
    def terms():
        return send_from_directory(str(public_dir), "terms.html")

    @app.route("/api/healthz")
    def healthz():
        return jsonify({"status": "ok", "signups": db.count_signups()})

    @app.route("/api/signup", methods=["POST"])
    def signup():
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        if not email or not EMAIL_RE.match(email):
            return jsonify({"error": "invalid email"}), 400

        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        ip_hash = _hash_ip(ip.split(",")[0].strip()) if ip else None
        referrer = request.headers.get("Referer")

        signup_id = db.insert_signup(email, ip_hash=ip_hash, referrer=referrer)
        # Email send is best-effort; failures are logged inside the client.
        email_client.send_confirmation(email)

        return jsonify({"signup_id": signup_id})

    return app


# Flask CLI entry
app = create_app()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_signup_endpoint.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server/app.py tests/test_signup_endpoint.py
git commit -m "feat(api): POST /api/signup with dedup and best-effort confirmation email

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: /api/qualifiers/<id> endpoint

**Files:**
- Modify: `~/dashaway/server/app.py` (add route)
- Create: `~/dashaway/tests/test_qualifiers_endpoint.py`

- [ ] **Step 1: Write the failing test**

Create `~/dashaway/tests/test_qualifiers_endpoint.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_qualifiers_endpoint.py -v
```

Expected: FAIL — endpoint doesn't exist yet.

- [ ] **Step 3: Add the route in `server/app.py`**

Add this route inside `create_app()`, just below the `/api/signup` route:

```python
    @app.route("/api/qualifiers/<int:signup_id>", methods=["POST"])
    def qualifiers(signup_id):
        if db.get_signup_by_id(signup_id) is None:
            return jsonify({"error": "signup not found"}), 404

        data = request.get_json(silent=True) or {}
        budget_bucket = data.get("budget_bucket")
        home_airport = data.get("home_airport")
        frustration = data.get("frustration")

        # Truncate frustration to 500 chars (matches spec)
        if frustration is not None:
            frustration = str(frustration)[:500]

        # Trim home airport
        if home_airport is not None:
            home_airport = str(home_airport).strip()[:32]

        try:
            db.upsert_qualifiers(
                signup_id,
                budget_bucket=budget_bucket,
                home_airport=home_airport,
                frustration=frustration,
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        return jsonify({"ok": True})
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_qualifiers_endpoint.py -v
pytest tests/ -v  # full suite still passes
```

Expected: all qualifier tests PASS, all previous tests still PASS.

- [ ] **Step 5: Commit**

```bash
git add server/app.py tests/test_qualifiers_endpoint.py
git commit -m "feat(api): POST /api/qualifiers/<id> with upsert and validation

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Self-host General Sans fonts

**Files:**
- Add to: `~/dashaway/public/fonts/`

- [ ] **Step 1: Download font files**

Fontshare doesn't expose a direct woff2 URL on their CDN; we need to download from their dashboard. Download these four weights manually:

1. Open https://www.fontshare.com/fonts/general-sans in a browser
2. Click "Download Family", get `General_Sans.zip`
3. Extract; locate the `Fonts/WEB/woff2/` subdirectory
4. Copy these four files into `~/dashaway/public/fonts/`:
   - `GeneralSans-Regular.woff2`
   - `GeneralSans-Medium.woff2`
   - `GeneralSans-Semibold.woff2`
   - `GeneralSans-Italic.woff2` (the regular-italic file)

(If Fontshare API access is available later, an automated download step can replace this manual step. For now, this is a 30-second human task.)

- [ ] **Step 2: Verify files exist**

```bash
ls -la ~/dashaway/public/fonts/
```

Expected: four `.woff2` files, each 20–40 KB.

- [ ] **Step 3: Commit**

```bash
git add public/fonts/
git commit -m "feat(fonts): self-host General Sans regular/medium/semibold/italic woff2

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Build index.html structure

**Files:**
- Create: `~/dashaway/public/index.html`

- [ ] **Step 1: Write `public/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Promptiv</title>
  <meta name="description" content="Somewhere new is closer than you think. Your budget is bigger than your map." />

  <!-- Open Graph -->
  <meta property="og:title" content="Promptiv" />
  <meta property="og:description" content="Somewhere new is closer than you think." />
  <meta property="og:url" content="https://promptiv.io" />
  <meta property="og:type" content="website" />

  <link rel="stylesheet" href="/styles.css" />
</head>
<body>
  <main class="teaser-frame">
    <h1 class="headline">Somewhere new is <em>closer</em> than you think.</h1>
    <p class="subhead">Your budget is bigger than your map.</p>

    <div class="card-stack" id="card-stack" aria-live="polite" aria-atomic="true">
      <article class="ex-card" data-card-idx="0">
        <div class="city">San Juan, Puerto Rico</div>
        <div class="meta">$342 · 4 nights · 1 stop · no passport</div>
        <div class="catch">catch: return lands at 11:40pm</div>
      </article>
      <article class="ex-card" data-card-idx="1">
        <div class="city">Lisbon, Portugal</div>
        <div class="meta">$612 · 7 nights · 1 stop</div>
        <div class="catch">catch: 13-hour door to door</div>
      </article>
      <article class="ex-card" data-card-idx="2">
        <div class="city">Mexico City</div>
        <div class="meta">$298 · 5 nights · nonstop</div>
        <div class="catch">catch: it's a city, not a beach</div>
      </article>
      <article class="ex-card" data-card-idx="3">
        <div class="city">Reykjavik, Iceland</div>
        <div class="meta">$789 · 6 nights · 1 stop</div>
        <div class="catch">catch: 5 hours of daylight in November</div>
      </article>
      <article class="ex-card" data-card-idx="4">
        <div class="city">Tokyo, Japan</div>
        <div class="meta">$1,287 · 10 nights · 1 stop</div>
        <div class="catch">catch: prices jump 40% during cherry blossom season</div>
      </article>
    </div>

    <form id="signup-form" class="form" novalidate>
      <label for="email-input" class="sr-only">Your email</label>
      <input
        id="email-input"
        class="email"
        type="email"
        name="email"
        placeholder="your email"
        required
        autocomplete="email"
      />
      <button class="btn" type="submit">Where can I go?</button>
    </form>

    <section class="thanks" id="thanks-state" hidden>
      <h2 class="ack">We're working on it.</h2>
      <p class="lead-in">Two quick optionals — they'll shape what we build first.</p>

      <div class="q">
        <div class="q-label">When you think about a trip, you're usually working with:</div>
        <div class="pick-group" id="budget-group" role="radiogroup" aria-label="Budget bucket">
          <button type="button" class="pick" data-pick="low" role="radio" aria-checked="false">Under $500</button>
          <button type="button" class="pick is-selected" data-pick="mid" role="radio" aria-checked="true">$500 – 1,200</button>
          <button type="button" class="pick" data-pick="stretch" role="radio" aria-checked="false">More than $1,200</button>
        </div>
      </div>

      <div class="q">
        <label for="airport-input" class="q-label">Home airport <span class="hint">(optional)</span></label>
        <input id="airport-input" class="text-input" placeholder="BNA, LAX, JFK…" maxlength="32" />
      </div>

      <div class="q">
        <label for="frustration-input" class="q-label">What's the worst part about planning a trip right now? <span class="hint">(optional)</span></label>
        <textarea id="frustration-input" class="text-input" placeholder="A sentence or two. We read these." maxlength="500"></textarea>
      </div>

      <div class="actions">
        <button type="button" id="qualifier-submit" class="done-btn">Share</button>
        <button type="button" id="qualifier-skip" class="skip-link">No thanks</button>
      </div>
    </section>

    <footer class="footer">
      © 2026 Promptiv · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a>
    </footer>
  </main>

  <!-- GSAP via CDN. Self-host before launch per spec. -->
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>
  <script src="/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Verify file is well-formed**

```bash
python3 -c "import html.parser as h; p = h.HTMLParser(); open('~/dashaway/public/index.html').read()" 2>&1 || true
# Or just visually inspect:
head -20 ~/dashaway/public/index.html
```

- [ ] **Step 3: Commit**

```bash
git add public/index.html
git commit -m "feat(html): teaser markup with rotating cards and thank-you state

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Stylesheet (styles.css)

**Files:**
- Create: `~/dashaway/public/styles.css`

- [ ] **Step 1: Write `public/styles.css`**

```css
/* General Sans — self-hosted */
@font-face {
  font-family: 'General Sans';
  src: url('/fonts/GeneralSans-Regular.woff2') format('woff2');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'General Sans';
  src: url('/fonts/GeneralSans-Italic.woff2') format('woff2');
  font-weight: 400;
  font-style: italic;
  font-display: swap;
}
@font-face {
  font-family: 'General Sans';
  src: url('/fonts/GeneralSans-Medium.woff2') format('woff2');
  font-weight: 500;
  font-style: normal;
  font-display: swap;
}
@font-face {
  font-family: 'General Sans';
  src: url('/fonts/GeneralSans-Semibold.woff2') format('woff2');
  font-weight: 600;
  font-style: normal;
  font-display: swap;
}

:root {
  --color-bg: #0a0814;
  --color-accent: #a78bfa;
  --color-text-primary: #ffffff;
  --color-text-secondary: #d8d4f0;
  --color-text-tertiary: #8b85b8;
  --color-text-quaternary: #7a749e;
  --color-text-quinary: #5a557a;
  --color-text-faint: #4a4670;
  --color-border: #2e2a48;
  --color-border-hover: #5a4d8a;
  --color-card-bg: rgba(167, 139, 250, 0.05);
  --color-card-border: rgba(167, 139, 250, 0.16);
  --color-link-underline: #2e2a48;
}

*, *::before, *::after { box-sizing: border-box; }

html, body {
  margin: 0;
  padding: 0;
  background: var(--color-bg);
  color: var(--color-text-secondary);
  font-family: 'General Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  -webkit-font-smoothing: antialiased;
  line-height: 1.5;
}

body { min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 24px; }

.teaser-frame {
  width: 100%;
  max-width: 540px;
  padding: 56px 36px 40px;
  display: flex;
  flex-direction: column;
  text-align: left;
  min-height: 620px;
}

@media (max-width: 540px) {
  .teaser-frame { padding: 40px 24px 28px; min-height: 0; }
}

.sr-only {
  position: absolute; width: 1px; height: 1px;
  padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
}

.headline {
  margin: 84px 0 18px;
  font-size: 36px;
  font-weight: 500;
  line-height: 1.08;
  color: var(--color-text-primary);
  letter-spacing: -0.025em;
}
.headline em {
  font-style: italic;
  color: var(--color-accent);
  font-weight: 400;
}

.subhead {
  margin: 0 0 36px;
  font-size: 15px;
  color: var(--color-text-tertiary);
  max-width: 420px;
  line-height: 1.55;
}

.card-stack {
  position: relative;
  height: 116px;
  margin-bottom: 36px;
}
.ex-card {
  position: absolute;
  inset: 0;
  background: var(--color-card-bg);
  border: 1px solid var(--color-card-border);
  border-radius: 8px;
  padding: 18px 20px;
  opacity: 0;
  will-change: opacity, transform;
}
.ex-card[data-card-idx="0"] { opacity: 1; }  /* JS-free fallback */
.ex-card .city {
  color: var(--color-text-primary);
  font-weight: 600;
  font-size: 15px;
  letter-spacing: -0.01em;
  margin-bottom: 6px;
}
.ex-card .meta {
  color: var(--color-text-quaternary);
  font-size: 12.5px;
  margin-bottom: 10px;
}
.ex-card .catch {
  color: var(--color-accent);
  font-size: 12.5px;
  font-style: italic;
  opacity: 0.85;
}

.form {
  display: flex;
  gap: 8px;
  margin-top: auto;
  flex-wrap: wrap;
}
.form.is-hidden { display: none; }
.email {
  flex: 1;
  min-width: 160px;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  padding: 11px 13px;
  color: var(--color-text-secondary);
  font-size: 13.5px;
  font-family: inherit;
}
.email:focus {
  outline: none;
  border-color: var(--color-accent);
}
.btn {
  background: var(--color-accent);
  color: var(--color-bg);
  border: none;
  border-radius: 5px;
  padding: 11px 18px;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
}

.thanks { display: block; margin-top: auto; }
.thanks[hidden] { display: none; }
.thanks .ack {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 500;
  color: var(--color-text-primary);
}
.thanks .lead-in {
  margin: 0 0 24px;
  color: var(--color-text-tertiary);
  font-size: 13.5px;
}
.thanks .q { margin-bottom: 20px; }
.thanks .q-label {
  display: block;
  color: var(--color-text-secondary);
  font-size: 13.5px;
  font-weight: 500;
  margin-bottom: 8px;
}
.thanks .q-label .hint {
  color: var(--color-text-quinary);
  font-weight: 400;
  font-size: 12px;
}

.pick-group { display: flex; gap: 6px; flex-wrap: wrap; }
.pick {
  background: transparent;
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  padding: 8px 14px;
  border-radius: 5px;
  font-size: 13px;
  cursor: pointer;
  transition: border-color 0.2s, color 0.2s, background 0.2s;
  font-family: inherit;
}
.pick:hover { border-color: var(--color-border-hover); color: var(--color-text-primary); }
.pick.is-selected {
  border-color: var(--color-accent);
  color: var(--color-accent);
  background: rgba(167, 139, 250, 0.08);
}
.pick:focus { outline: 2px solid var(--color-accent); outline-offset: 2px; }

.text-input {
  width: 100%;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: 5px;
  padding: 10px 13px;
  color: var(--color-text-secondary);
  font-size: 13.5px;
  font-family: inherit;
}
.text-input:focus {
  outline: none;
  border-color: var(--color-accent);
}
textarea.text-input { min-height: 64px; resize: vertical; }

.actions { display: flex; gap: 14px; align-items: center; margin-top: 12px; }
.done-btn {
  background: var(--color-accent);
  color: var(--color-bg);
  border: none;
  border-radius: 5px;
  padding: 11px 18px;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
}
.skip-link {
  background: transparent;
  border: none;
  color: var(--color-text-quaternary);
  font-size: 12.5px;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 1px;
  cursor: pointer;
  font-family: inherit;
}
.skip-link:hover { color: var(--color-text-secondary); }

.footer {
  margin-top: 24px;
  font-size: 10.5px;
  color: var(--color-text-faint);
}
.footer a {
  color: var(--color-text-quinary);
  text-decoration: underline;
  text-underline-offset: 2px;
  text-decoration-color: var(--color-link-underline);
}
.footer a:hover { color: var(--color-text-tertiary); }

@media (prefers-reduced-motion: reduce) {
  .ex-card { opacity: 0 !important; transform: none !important; transition: none !important; }
  .ex-card[data-card-idx="0"] { opacity: 1 !important; }
}
```

- [ ] **Step 2: Commit**

```bash
git add public/styles.css
git commit -m "feat(css): stylesheet with self-hosted General Sans and design tokens

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Client-side JavaScript (app.js)

**Files:**
- Create: `~/dashaway/public/app.js`

- [ ] **Step 1: Write `public/app.js`**

```javascript
/* global gsap */
(function () {
  'use strict';

  // ---------- Card rotation ----------

  function initCardRotation() {
    var reduceMotion =
      window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var cards = document.querySelectorAll('#card-stack .ex-card');
    if (!cards.length) return;

    if (reduceMotion || typeof gsap === 'undefined') {
      cards[0].style.opacity = '1';
      return;
    }

    gsap.set(cards, { opacity: 0, y: 6 });
    gsap.set(cards[0], { opacity: 1, y: 0 });

    var current = 0;
    var DWELL_MS = 6000;
    var FADE_S = 1.2;

    setInterval(function () {
      var next = (current + 1) % cards.length;
      var tl = gsap.timeline();
      tl.to(cards[current], { opacity: 0, y: -6, duration: FADE_S, ease: 'power4.out' })
        .fromTo(cards[next],
          { opacity: 0, y: 6 },
          { opacity: 1, y: 0, duration: FADE_S, ease: 'power4.out' },
          '-=' + (FADE_S * 0.5));
      current = next;
    }, DWELL_MS);
  }

  // ---------- Form submission ----------

  var state = { signupId: null, budgetBucket: 'mid' };

  function showThanks() {
    document.getElementById('signup-form').classList.add('is-hidden');
    document.getElementById('thanks-state').hidden = false;
  }

  function initSignupForm() {
    var form = document.getElementById('signup-form');
    if (!form) return;

    form.addEventListener('submit', function (evt) {
      evt.preventDefault();
      var emailInput = document.getElementById('email-input');
      var email = (emailInput.value || '').trim();
      if (!email) { emailInput.focus(); return; }

      var btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      btn.textContent = '…';

      fetch('/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
      })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        if (!res.ok) {
          btn.disabled = false;
          btn.textContent = 'Where can I go?';
          emailInput.focus();
          return;
        }
        state.signupId = res.body.signup_id;
        showThanks();
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = 'Where can I go?';
      });
    });
  }

  // ---------- Pick (budget bucket) buttons ----------

  function initPickButtons() {
    var picks = document.querySelectorAll('#budget-group .pick');
    picks.forEach(function (btn) {
      btn.addEventListener('click', function () {
        picks.forEach(function (b) {
          b.classList.remove('is-selected');
          b.setAttribute('aria-checked', 'false');
        });
        btn.classList.add('is-selected');
        btn.setAttribute('aria-checked', 'true');
        state.budgetBucket = btn.getAttribute('data-pick');
      });
    });
  }

  // ---------- Qualifier submit / skip ----------

  function initQualifierActions() {
    var submitBtn = document.getElementById('qualifier-submit');
    var skipBtn = document.getElementById('qualifier-skip');

    function dismissThanks() {
      // Replace thanks state with a quiet final message
      var thanks = document.getElementById('thanks-state');
      thanks.innerHTML = '<p class="lead-in">Thanks. We’ll be in touch.</p>';
    }

    if (submitBtn) {
      submitBtn.addEventListener('click', function () {
        if (!state.signupId) { dismissThanks(); return; }
        var payload = {
          budget_bucket: state.budgetBucket,
          home_airport: (document.getElementById('airport-input').value || '').trim() || null,
          frustration: (document.getElementById('frustration-input').value || '').trim() || null
        };
        submitBtn.disabled = true;
        submitBtn.textContent = '…';

        fetch('/api/qualifiers/' + state.signupId, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }).then(function () { dismissThanks(); })
          .catch(function () { dismissThanks(); });
      });
    }
    if (skipBtn) {
      skipBtn.addEventListener('click', dismissThanks);
    }
  }

  // ---------- Bootstrap ----------

  document.addEventListener('DOMContentLoaded', function () {
    initCardRotation();
    initSignupForm();
    initPickButtons();
    initQualifierActions();
  });
})();
```

- [ ] **Step 2: Commit**

```bash
git add public/app.js
git commit -m "feat(js): rotation, signup form, qualifier handling

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Privacy and Terms stub pages

**Files:**
- Create: `~/dashaway/public/privacy.html`
- Create: `~/dashaway/public/terms.html`

- [ ] **Step 1: Write `public/privacy.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Privacy — Promptiv</title>
  <link rel="stylesheet" href="/styles.css" />
  <style>
    .legal { max-width: 640px; margin: 80px auto; padding: 0 24px; color: var(--color-text-secondary); }
    .legal h1 { color: var(--color-text-primary); font-size: 28px; font-weight: 500; }
    .legal h2 { color: var(--color-text-primary); font-size: 18px; margin-top: 32px; font-weight: 500; }
    .legal p, .legal li { font-size: 14.5px; line-height: 1.65; }
    .legal a { color: var(--color-accent); }
    .legal .back { font-size: 12.5px; color: var(--color-text-quaternary); margin-bottom: 24px; display: inline-block; }
  </style>
</head>
<body>
  <main class="legal">
    <a class="back" href="/">← Promptiv</a>
    <h1>Privacy</h1>
    <p>Last updated: 2026-05-25.</p>

    <h2>What we collect</h2>
    <p>If you sign up to be notified about Promptiv, we collect:</p>
    <ul>
      <li>The email address you submit</li>
      <li>A hashed (one-way SHA-256) version of your IP, used only to dedupe duplicate signups</li>
      <li>The referrer URL if your browser sends one</li>
      <li>Optional answers you provide on the post-signup screen (budget bucket, home airport, biggest travel frustration)</li>
    </ul>

    <h2>What we don't collect</h2>
    <p>No cookies. No third-party analytics. No tracking pixels. No payment information.</p>

    <h2>How we use it</h2>
    <p>To email you when there is a real product to share. To learn what kind of trips matter most to people considering Promptiv. We don't sell or share your data.</p>

    <h2>Deletion</h2>
    <p>Email <a href="mailto:adam@distillworks.com">adam@distillworks.com</a> and ask us to delete your signup. We will do so within 7 days and reply to confirm.</p>

    <h2>Contact</h2>
    <p>Questions or concerns: <a href="mailto:adam@distillworks.com">adam@distillworks.com</a>.</p>
  </main>
</body>
</html>
```

- [ ] **Step 2: Write `public/terms.html`**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Terms — Promptiv</title>
  <link rel="stylesheet" href="/styles.css" />
  <style>
    .legal { max-width: 640px; margin: 80px auto; padding: 0 24px; color: var(--color-text-secondary); }
    .legal h1 { color: var(--color-text-primary); font-size: 28px; font-weight: 500; }
    .legal h2 { color: var(--color-text-primary); font-size: 18px; margin-top: 32px; font-weight: 500; }
    .legal p, .legal li { font-size: 14.5px; line-height: 1.65; }
    .legal a { color: var(--color-accent); }
    .legal .back { font-size: 12.5px; color: var(--color-text-quaternary); margin-bottom: 24px; display: inline-block; }
  </style>
</head>
<body>
  <main class="legal">
    <a class="back" href="/">← Promptiv</a>
    <h1>Terms</h1>
    <p>Last updated: 2026-05-25.</p>

    <h2>What Promptiv is right now</h2>
    <p>Promptiv is currently a teaser page for a product that does not yet exist. Signing up adds your email to a list and grants no commitment, no purchase, and no obligation.</p>

    <h2>No service is provided</h2>
    <p>There is no product, no booking engine, no travel reservation system behind this page. Information shown in the rotating example cards is illustrative and may not reflect current prices or availability.</p>

    <h2>If we launch</h2>
    <p>When the actual product launches, these terms will be replaced with terms covering that service. Until then, this page exists for one purpose: to gauge interest.</p>

    <h2>Limitation of liability</h2>
    <p>This site is provided as-is. We make no warranties. Maximum liability is limited to the amount you have paid us, which is zero.</p>

    <h2>Contact</h2>
    <p><a href="mailto:adam@distillworks.com">adam@distillworks.com</a></p>
  </main>
</body>
</html>
```

- [ ] **Step 3: Commit**

```bash
git add public/privacy.html public/terms.html
git commit -m "feat(legal): privacy and terms stubs

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Run the app locally and verify

**Files:** (no new files — verification step)

- [ ] **Step 1: Create local venv and install deps**

```bash
cd ~/dashaway
python3 -m venv .venv
source .venv/bin/activate
pip install -r server/requirements.txt
```

- [ ] **Step 2: Copy and populate `.env`**

```bash
cp .env.example .env
# Edit .env: set RESEND_API_KEY (real key), DATABASE_PATH to ./teaser.dev.sqlite
nano .env  # or your editor of choice
```

- [ ] **Step 3: Initialize the dev database**

```bash
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
python3 -c "from server.migrations import init_schema; import os; init_schema(os.environ['DATABASE_PATH']); print('schema ready at', os.environ['DATABASE_PATH'])"
```

Expected output: `schema ready at ./teaser.dev.sqlite`

- [ ] **Step 4: User starts Flask manually in a separate terminal**

Per user CLAUDE.md, the agent does not launch dev servers. The user runs:

```bash
cd ~/dashaway
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
flask run --port 5000
```

The user opens `http://localhost:5000` and verifies:
- Page renders
- Cards rotate
- General Sans is loaded (check Network tab; font files load with 200)
- Submitting email transitions to thank-you state
- Selecting budget bucket / typing airport / clicking "Share" works
- Refresh: page works without JavaScript blocked? (DevTools → block JS, reload)
- `prefers-reduced-motion`: macOS System Settings → Accessibility → Display → Reduce motion. Reload. Cards should not rotate.

User reports back to the agent with a checklist of pass/fail.

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v
```

Expected: all tests pass (25+ tests across migrations, db, email, signup, qualifiers).

- [ ] **Step 6: Commit nothing yet — verification is exploratory**

If user finds issues in Step 4, return to the relevant task and fix. Otherwise proceed.

---

## Task 13: Playwright end-to-end test

**Files:**
- Create: `~/dashaway/tests/e2e/test_teaser_flow.py`

- [ ] **Step 1: Install Playwright browsers**

```bash
cd ~/dashaway
source .venv/bin/activate
playwright install chromium
```

- [ ] **Step 2: Write the E2E test**

Create `~/dashaway/tests/e2e/test_teaser_flow.py`:

```python
"""End-to-end smoke test for the teaser page.

Run this against a locally running Flask app:
    # Terminal 1 (started by user):
    flask run --port 5000

    # Terminal 2:
    pytest tests/e2e/test_teaser_flow.py -v
"""
import os
import pytest
from playwright.sync_api import sync_playwright, expect


BASE_URL = os.environ.get("PROMPTIV_BASE_URL", "http://localhost:5000")


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        yield page
        browser.close()


def test_page_loads_with_headline(page):
    page.goto(BASE_URL)
    expect(page.locator("h1.headline")).to_contain_text("Somewhere new is")
    expect(page.locator(".subhead")).to_contain_text("Your budget is bigger than your map")


def test_first_card_visible_on_load(page):
    page.goto(BASE_URL)
    first_card = page.locator('.ex-card[data-card-idx="0"]')
    expect(first_card).to_be_visible()


def test_signup_flow_transitions_to_thanks(page):
    page.goto(BASE_URL)
    page.fill("#email-input", "playwright-e2e@example.com")
    page.click("button[type='submit']")
    expect(page.locator("#thanks-state")).to_be_visible(timeout=5000)
    expect(page.locator(".ack")).to_contain_text("We're working on it")


def test_qualifier_submit_dismisses_thanks(page):
    page.goto(BASE_URL)
    page.fill("#email-input", "playwright-e2e-2@example.com")
    page.click("button[type='submit']")
    expect(page.locator("#thanks-state")).to_be_visible(timeout=5000)

    page.click('.pick[data-pick="stretch"]')
    page.fill("#airport-input", "BNA")
    page.fill("#frustration-input", "everything is overwhelming")
    page.click("#qualifier-submit")

    # After submit, the thanks block should be replaced with a quiet message
    expect(page.locator("#thanks-state")).to_contain_text("Thanks. We'll be in touch.", timeout=5000)


def test_qualifier_skip_dismisses_thanks(page):
    page.goto(BASE_URL)
    page.fill("#email-input", "playwright-e2e-3@example.com")
    page.click("button[type='submit']")
    expect(page.locator("#thanks-state")).to_be_visible(timeout=5000)

    page.click("#qualifier-skip")
    expect(page.locator("#thanks-state")).to_contain_text("Thanks", timeout=5000)


def test_privacy_page_loads(page):
    page.goto(BASE_URL + "/privacy")
    expect(page.locator("h1")).to_contain_text("Privacy")


def test_terms_page_loads(page):
    page.goto(BASE_URL + "/terms")
    expect(page.locator("h1")).to_contain_text("Terms")
```

- [ ] **Step 3: Verify E2E tests pass against a running Flask**

User starts Flask in a separate terminal (Task 12 Step 4), then runs:

```bash
pytest tests/e2e/test_teaser_flow.py -v
```

Expected: all 7 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/
git commit -m "test(e2e): Playwright flow covering signup, qualifiers, privacy, terms

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 14: Production nginx + systemd configs

**Files:**
- Create: `~/dashaway/deploy/nginx-promptiv.conf`
- Create: `~/dashaway/deploy/promptiv.service`

- [ ] **Step 1: Write nginx config**

Create `~/dashaway/deploy/nginx-promptiv.conf`:

```nginx
# /etc/nginx/sites-available/promptiv.io
# Serves static assets from /srv/promptiv/public.
# Proxies /api/* to the Flask app on localhost:8000.

server {
    listen 80;
    listen [::]:80;
    server_name promptiv.io www.promptiv.io;

    # Redirect HTTP to HTTPS (after Certbot has run)
    return 301 https://promptiv.io$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name promptiv.io www.promptiv.io;

    # SSL — managed by certbot
    ssl_certificate     /etc/letsencrypt/live/promptiv.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/promptiv.io/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;

    root /srv/promptiv/public;
    index index.html;

    # API proxy
    location /api/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 10s;
    }

    # Long cache for fonts (immutable)
    location /fonts/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        access_log off;
    }

    # Short cache for css/js
    location ~* \.(css|js)$ {
        expires 5m;
        add_header Cache-Control "public";
    }

    # Privacy / Terms — clean URLs
    location = /privacy {
        try_files /privacy.html =404;
    }
    location = /terms {
        try_files /terms.html =404;
    }

    # Fallback
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 2: Write systemd unit**

Create `~/dashaway/deploy/promptiv.service`:

```ini
[Unit]
Description=Promptiv teaser Flask app (gunicorn)
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/srv/promptiv
Environment="PYTHONUNBUFFERED=1"
EnvironmentFile=/srv/promptiv/.env
ExecStart=/srv/promptiv/.venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/promptiv/access.log \
    --error-logfile /var/log/promptiv/error.log \
    server.app:app
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 3: Add gunicorn to requirements**

Append to `~/dashaway/server/requirements.txt`:

```
gunicorn==23.0.0
```

- [ ] **Step 4: Commit**

```bash
git add deploy/nginx-promptiv.conf deploy/promptiv.service server/requirements.txt
git commit -m "deploy: nginx config and systemd unit for production

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 15: Deployment runbook

**Files:**
- Create: `~/dashaway/deploy/DEPLOY.md`

- [ ] **Step 1: Write the runbook**

Create `~/dashaway/deploy/DEPLOY.md`:

````markdown
# Promptiv Teaser — Deployment Runbook

Target: `Promptiv-main` server (root@promptiv.io). One-time setup, then incremental deploys.

## One-time setup (run once on the server)

### 1. Back up the current placeholder

```bash
ssh root@promptiv.io
mkdir -p /root/backups
cp -r /var/www/promptiv.io /root/backups/promptiv-placeholder-$(date +%Y%m%d-%H%M%S)
# Or wherever the current placeholder lives — verify with: nginx -T | grep -A20 promptiv
```

### 2. System prep (security update + Python + nginx + certbot)

```bash
# 347-day uptime — kernel update is overdue. Schedule a reboot window.
apt update && apt upgrade -y
apt install -y python3.11 python3.11-venv nginx certbot python3-certbot-nginx
# If reboot needed, do it here:
reboot
# Then reconnect.
```

### 3. Create app directory and user

```bash
mkdir -p /srv/promptiv /var/log/promptiv /var/lib/promptiv
chown -R www-data:www-data /var/log/promptiv /var/lib/promptiv
```

### 4. Initial code deploy from local

Run from your laptop (`~/dashaway/`):

```bash
rsync -avz --delete \
    --exclude='.venv' --exclude='.git' --exclude='*.sqlite' \
    --exclude='__pycache__' --exclude='.env' --exclude='.superpowers' \
    --exclude='node_modules' \
    ~/dashaway/ root@promptiv.io:/srv/promptiv/
```

### 5. Server-side: install deps and create venv

```bash
ssh root@promptiv.io
cd /srv/promptiv
python3.11 -m venv .venv
.venv/bin/pip install -r server/requirements.txt
chown -R www-data:www-data /srv/promptiv
```

### 6. Create production `.env`

```bash
# On server:
cp /srv/promptiv/.env.example /srv/promptiv/.env
nano /srv/promptiv/.env
```

Set:
- `RESEND_API_KEY` (real production key — separate from dev)
- `RESEND_FROM=team@mail.distillworks.com` (or new `team@promptiv.io` if set up)
- `DATABASE_PATH=/var/lib/promptiv/teaser.sqlite`
- `SECRET_KEY` (generate: `python3 -c "import secrets; print(secrets.token_hex(32))"`)

```bash
chmod 600 /srv/promptiv/.env
chown www-data:www-data /srv/promptiv/.env
```

### 7. Initialize the production database

```bash
sudo -u www-data /srv/promptiv/.venv/bin/python3 -c \
  "from server.migrations import init_schema; init_schema('/var/lib/promptiv/teaser.sqlite')"
ls -la /var/lib/promptiv/teaser.sqlite
```

### 8. Install systemd unit

```bash
cp /srv/promptiv/deploy/promptiv.service /etc/systemd/system/promptiv.service
systemctl daemon-reload
systemctl enable promptiv.service
systemctl start promptiv.service
systemctl status promptiv.service  # verify "active (running)"
```

### 9. Install nginx config

```bash
cp /srv/promptiv/deploy/nginx-promptiv.conf /etc/nginx/sites-available/promptiv.io
ln -sf /etc/nginx/sites-available/promptiv.io /etc/nginx/sites-enabled/promptiv.io
# Remove the old placeholder config if it exists
rm -f /etc/nginx/sites-enabled/promptiv.io.old  # adjust name as needed
nginx -t  # syntax check
```

### 10. SSL via certbot

```bash
# First, comment out the SSL block in nginx-promptiv.conf temporarily — certbot will add it back
# Or use --nginx flag to let certbot configure:
certbot --nginx -d promptiv.io -d www.promptiv.io
# Reply to prompts. Email, agree, redirect HTTP→HTTPS.
```

### 11. Reload nginx

```bash
nginx -t && systemctl reload nginx
```

### 12. Smoke test

```bash
curl -I https://promptiv.io
# Expect: HTTP/2 200

curl -s -X POST https://promptiv.io/api/signup \
    -H "Content-Type: application/json" \
    -d '{"email":"deploy-smoke-test@example.com"}'
# Expect: {"signup_id": <int>}
```

Then in a browser, open https://promptiv.io — visually verify the teaser.

If the smoke test signup returns a real `signup_id`, remove it from the database:

```bash
sqlite3 /var/lib/promptiv/teaser.sqlite "DELETE FROM signups WHERE email = 'deploy-smoke-test@example.com';"
```

## Incremental deploys (every change after initial)

```bash
# From laptop:
cd ~/dashaway
rsync -avz \
    --exclude='.venv' --exclude='.git' --exclude='*.sqlite' \
    --exclude='__pycache__' --exclude='.env' --exclude='.superpowers' \
    --exclude='node_modules' \
    ~/dashaway/ root@promptiv.io:/srv/promptiv/

# Then on the server:
ssh root@promptiv.io "systemctl restart promptiv.service && systemctl reload nginx"
```

For Python-only changes, just `systemctl restart promptiv.service`. For static-asset-only changes, no restart needed (nginx picks them up on next request).

## Rollback

```bash
# On server:
cp -r /root/backups/promptiv-placeholder-<timestamp>/* /srv/promptiv/
systemctl restart promptiv.service
systemctl reload nginx
```

## Monitoring

```bash
# Live tail of the app log:
tail -f /var/log/promptiv/error.log

# Last 100 access log lines:
tail -n 100 /var/log/promptiv/access.log

# Signup count:
sqlite3 /var/lib/promptiv/teaser.sqlite "SELECT COUNT(*) FROM signups;"

# Recent signups (last 20):
sqlite3 /var/lib/promptiv/teaser.sqlite \
    "SELECT id, email, created_at FROM signups ORDER BY id DESC LIMIT 20;"

# Recent qualifiers:
sqlite3 /var/lib/promptiv/teaser.sqlite \
    "SELECT s.email, q.budget_bucket, q.home_airport, q.frustration
     FROM qualifiers q JOIN signups s ON q.signup_id = s.id
     ORDER BY q.id DESC LIMIT 20;"
```

## Backup

The SQLite file at `/var/lib/promptiv/teaser.sqlite` is the entire data store. Back it up regularly:

```bash
# Manual snapshot:
sqlite3 /var/lib/promptiv/teaser.sqlite ".backup /root/backups/teaser-$(date +%Y%m%d-%H%M%S).sqlite"

# Add to cron (daily at 03:30 UTC):
echo "30 3 * * * sqlite3 /var/lib/promptiv/teaser.sqlite \".backup /root/backups/teaser-\$(date +\\%Y\\%m\\%d).sqlite\" && find /root/backups -name 'teaser-*.sqlite' -mtime +30 -delete" | crontab -
```
````

- [ ] **Step 2: Commit**

```bash
git add deploy/DEPLOY.md
git commit -m "docs(deploy): runbook for production deployment to Promptiv-main

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 16: Execute the production deploy

**Files:** (no new files — runs the runbook)

- [ ] **Step 1: User runs the one-time setup from `deploy/DEPLOY.md`**

User follows DEPLOY.md sections 1-11 against `root@promptiv.io`.

Agent assists by:
- Suggesting exact rsync commands for sync
- Helping debug nginx config errors via `nginx -t` output
- Verifying systemd unit status
- Helping resolve any certbot prompts

- [ ] **Step 2: User runs DEPLOY.md section 12 (smoke test)**

```bash
curl -I https://promptiv.io          # 200
curl -X POST https://promptiv.io/api/signup -H "Content-Type: application/json" -d '{"email":"deploy-smoke@example.com"}'
```

Expected: HTTP 200 + `{"signup_id": <int>}` response.

- [ ] **Step 3: Browser-based smoke test**

User opens https://promptiv.io in a real browser and verifies:
- Page loads cleanly, fonts render
- Cards rotate
- Email submit works → thank-you state appears
- Budget pick + airport + frustration → "Share" works
- A confirmation email arrives at the test address (check Resend dashboard or inbox)

- [ ] **Step 4: Remove smoke-test rows from production DB**

```bash
ssh root@promptiv.io "sqlite3 /var/lib/promptiv/teaser.sqlite \"DELETE FROM signups WHERE email LIKE '%smoke%' OR email LIKE '%e2e%' OR email LIKE '%example.com';\""
```

- [ ] **Step 5: Final commit (mark deployment done)**

```bash
cd ~/dashaway
echo "Deployed to production: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> deploy/DEPLOYMENTS.log
git add deploy/DEPLOYMENTS.log
git commit -m "deploy: initial production rollout

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review (completed by author)

**Spec coverage check:**

| Spec section | Implementing task(s) |
|---|---|
| §1 Purpose | All tasks |
| §2 Goals/success criteria | Task 5, 6 (data capture); Task 15 (monitoring queries) |
| §3 User flow | Tasks 8, 9, 10 |
| §4 Visual design (colors, type, layout) | Tasks 7, 9 |
| §5 Copy | Task 8 |
| §6 Example trip cards | Task 8 |
| §7 Motion (GSAP, ease, reduced-motion) | Task 10 |
| §8 Accessibility | Tasks 8, 9, 10 (aria, focus, contrast) |
| §9 Form and data | Tasks 2, 3, 5, 6 |
| §10 Implementation architecture | Tasks 1-7, 14, 15 |
| §11 Out of scope | Not implemented (correctly excluded) |
| §12 Open questions | Sender domain → DEPLOY.md addresses |

All spec sections have implementing tasks.

**Placeholder scan:** Searched for "TBD", "TODO", "implement later", "Add appropriate error handling", "Write tests for the above". None found. All steps contain executable content.

**Type/name consistency:** Verified across tasks:
- `signup_id` is consistent throughout (DB column, JSON key, route parameter)
- `budget_bucket` uses lowercase values `low | mid | stretch` consistently
- `init_schema()` signature matches between definition (Task 2) and callers (Tasks 3, 5, 12, DEPLOY.md)
- Email field validation (lowercase + strip) defined in Task 5 and tested in Task 5

No inconsistencies found.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-25-promptiv-teaser.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Most appropriate when you want to make progress without manually executing each step.

**2. Inline Execution** — Execute tasks in this session using executing-plans. Batch execution with checkpoints for your review at predetermined points.

**Which approach?**
