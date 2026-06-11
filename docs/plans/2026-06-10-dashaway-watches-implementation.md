# DashAway Watches — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship DashAway Watches v1 per the approved spec (`docs/plans/2026-06-10-dashaway-watches-design.md`): users create one free fare watch (route + flexible window), confirmed by double opt-in; a nightly batch prices each watched route with one SearchDates request; a layered alert brain emails only when decision-worthy; a Sunday pulse proves the watching; ops tripwires protect the shared warmed IP.

**Architecture:** Five new server modules behind the existing Flask app and SQLite DB. `watches.py` (CRUD + validation, tokens), `watch_brain.py` (pure trigger logic over `fare_observations`), `watch_runner.py` (nightly batch: scan → write → decide → send → ops summary, abort-on-429), `watch_emails.py` (alert + pulse composition, DashAway email palette), `watch_pulse.py` (Sunday sender). New endpoints in `app.py` follow the `/api/signup` pattern; `/watch` is a static page; `/watch/confirm` + `/watch/manage` are Flask-served. Two new systemd timers. No new storage for price series: a watch's nightly best is derived from `fare_observations` (`source='watch'`), so the archive remains the single source of truth.

**Tech stack:** existing only — Flask, SQLite, fli (`FliClient` wrapper with `FLI_MOCK`), Resend, systemd, nginx. No new dependencies.

**Conventions this plan follows (verified in repo):**
- Schema lives in `server/migrations.py` `SCHEMA` constant; deploy applies `init_schema`.
- `fare_observations` UNIQUE key includes `source`, so `source='watch'` rows never collide with `'fli'`.
- `FliClient.search_dates(origin, dest, start_date: date, end_date: date, trip_nights)` exists with mock mode; `price_refresh._plausible` guards $40–3500.
- Email via `email_client` (env `RESEND_API_KEY`/`RESEND_FROM`); digest palette `CREAM/#f5f3ee, INK/#1a1a1f, ACCENT/#a78bfa`.
- Tests: `tests/conftest.py` provides `temp_db_path`, `app`, `client` fixtures; run `python -m pytest` (in `.venv`).
- Tokens: `secrets.token_urlsafe(24)`; unsubscribe-style flows return RFC-8058-ish responses.

**Run command for every test step:** `cd ~/promptiv && .venv/bin/python -m pytest <file> -q`

---

### Task 1: Schema — `watches` + `watch_events`

**Files:**
- Modify: `server/migrations.py` (SCHEMA constant)
- Test: `tests/test_watches_schema.py`

- [ ] **Step 1.1: Failing test**

`tests/test_watches_schema.py`:
```python
import sqlite3
from server.migrations import init_schema


def test_watch_tables_exist(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(watches)")}
    assert {"id", "email", "origin_iata", "dest_iata", "window_start",
            "window_end", "trip_nights", "ceiling_usd", "status",
            "manage_token", "ip_hash", "created_at", "confirmed_at",
            "last_alert_at"} <= cols
    ev = {r[1] for r in conn.execute("PRAGMA table_info(watch_events)")}
    assert {"id", "watch_id", "kind", "sent_at", "best_price",
            "best_depart", "best_return", "trigger"} <= ev


def test_manage_token_unique(temp_db_path):
    init_schema(temp_db_path)
    conn = sqlite3.connect(temp_db_path)
    conn.execute("INSERT INTO watches (email, origin_iata, dest_iata, window_start, window_end, trip_nights, status, manage_token, created_at) VALUES ('a@b.c','BNA','PLS','2026-11-01','2027-01-31',7,'pending','tok1','2026-06-10')")
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO watches (email, origin_iata, dest_iata, window_start, window_end, trip_nights, status, manage_token, created_at) VALUES ('x@y.z','BNA','GRR','2026-11-01','2027-01-31',7,'pending','tok1','2026-06-10')")
```

- [ ] **Step 1.2: Run, verify fail** (`no such table: watches`)

- [ ] **Step 1.3: Add to SCHEMA in `server/migrations.py`** (append inside the SCHEMA string, before the closing quotes, after the fare_observations block):

```sql
-- Fare watches: one user-defined route+window watched nightly (Watches v1).
CREATE TABLE IF NOT EXISTS watches (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         TEXT NOT NULL,
    origin_iata   TEXT NOT NULL,
    dest_iata     TEXT NOT NULL,
    window_start  TEXT NOT NULL,
    window_end    TEXT NOT NULL,
    trip_nights   INTEGER NOT NULL,
    ceiling_usd   INTEGER,
    status        TEXT NOT NULL DEFAULT 'pending',  -- pending|active|paused|deleted
    manage_token  TEXT NOT NULL UNIQUE,
    ip_hash       TEXT,
    created_at    TEXT NOT NULL,
    confirmed_at  TEXT,
    last_alert_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_watches_status ON watches(status);
CREATE INDEX IF NOT EXISTS idx_watches_email ON watches(email);

-- Watch event log: powers the 1-alert-per-week covenant + auditing.
CREATE TABLE IF NOT EXISTS watch_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    watch_id    INTEGER NOT NULL REFERENCES watches(id),
    kind        TEXT NOT NULL,            -- confirm|alert|pulse
    sent_at     TEXT NOT NULL,
    best_price  INTEGER,
    best_depart TEXT,
    best_return TEXT,
    trigger     TEXT                       -- drop|percentile|ceiling
);
CREATE INDEX IF NOT EXISTS idx_watch_events_watch ON watch_events(watch_id, kind, sent_at);
```

- [ ] **Step 1.4: Run, verify pass**
- [ ] **Step 1.5: Commit** `git add -A && git commit -m "feat(watches): schema for watches + watch_events"`

---

### Task 2: Core domain — `server/watches.py`

**Files:**
- Create: `server/watches.py`
- Test: `tests/test_watches_core.py`

- [ ] **Step 2.1: Failing tests**

`tests/test_watches_core.py`:
```python
from datetime import date
import sqlite3
import pytest
from server.migrations import init_schema
from server import watches

TODAY = date(2026, 6, 10)


@pytest.fixture
def conn(temp_db_path):
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _mk(conn, **kw):
    args = dict(email="a@b.co", origin="BNA", dest="PLS",
                window_start="2026-11-01", window_end="2027-01-31",
                trip_nights=7, ceiling_usd=450, ip_hash="h", today=TODAY)
    args.update(kw)
    return watches.create_watch(conn, **args)


def test_create_returns_token_and_pending(conn):
    w = _mk(conn)
    assert len(w["manage_token"]) >= 24
    row = conn.execute("SELECT * FROM watches WHERE id=?", (w["id"],)).fetchone()
    assert row["status"] == "pending"
    assert row["origin_iata"] == "BNA" and row["dest_iata"] == "PLS"


def test_validation_rules(conn):
    with pytest.raises(ValueError, match="airport"):
        _mk(conn, origin="QQQ")
    with pytest.raises(ValueError, match="airport"):
        _mk(conn, dest="bad")
    with pytest.raises(ValueError, match="origin"):
        _mk(conn, dest="BNA")                       # origin == dest
    with pytest.raises(ValueError, match="nights"):
        _mk(conn, trip_nights=2)
    with pytest.raises(ValueError, match="nights"):
        _mk(conn, trip_nights=15)
    with pytest.raises(ValueError, match="window"):
        _mk(conn, window_start="2026-06-01")        # not >= tomorrow
    with pytest.raises(ValueError, match="window"):
        _mk(conn, window_end="2027-06-01")          # span > 185 days
    with pytest.raises(ValueError, match="window"):
        _mk(conn, window_start="2027-04-15", window_end="2027-04-10")
    with pytest.raises(ValueError, match="email"):
        _mk(conn, email="not-an-email")


def test_one_active_watch_per_email(conn):
    _mk(conn)
    with pytest.raises(ValueError, match="one watch"):
        _mk(conn, dest="GRR")
    # a deleted watch frees the slot
    conn.execute("UPDATE watches SET status='deleted'")
    _mk(conn, dest="GRR")


def test_confirm_flow(conn):
    w = _mk(conn)
    assert watches.confirm_watch(conn, w["manage_token"]) is True
    row = conn.execute("SELECT status, confirmed_at FROM watches").fetchone()
    assert row["status"] == "active" and row["confirmed_at"]
    assert watches.confirm_watch(conn, "nope") is False


def test_manage_actions(conn):
    w = _mk(conn)
    watches.confirm_watch(conn, w["manage_token"])
    assert watches.set_status(conn, w["manage_token"], "paused") is True
    assert conn.execute("SELECT status FROM watches").fetchone()[0] == "paused"
    assert watches.set_status(conn, w["manage_token"], "active") is True
    assert watches.set_status(conn, w["manage_token"], "deleted") is True
    assert watches.set_status(conn, "nope", "paused") is False
    with pytest.raises(ValueError):
        watches.set_status(conn, w["manage_token"], "exploded")


def test_ip_rate_limit(conn):
    for i in range(5):
        w = _mk(conn, email=f"u{i}@x.co")
        conn.execute("UPDATE watches SET status='deleted' WHERE id=?", (w["id"],))
    with pytest.raises(ValueError, match="too many"):
        _mk(conn, email="u9@x.co")


def test_active_watches_listing(conn):
    w = _mk(conn)
    assert watches.active_watches(conn) == []          # pending isn't active
    watches.confirm_watch(conn, w["manage_token"])
    acts = watches.active_watches(conn)
    assert len(acts) == 1 and acts[0]["origin_iata"] == "BNA"
```

- [ ] **Step 2.2: Run, verify fail**

- [ ] **Step 2.3: Implement `server/watches.py`**

```python
"""Watches v1: CRUD + validation. No accounts — a watch is email + manage_token."""
import re
import secrets
from datetime import date, datetime, timedelta, timezone

from fli.models.airport import Airport

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
NIGHTS_MIN, NIGHTS_MAX = 3, 14
WINDOW_SPAN_MAX_DAYS = 185
WINDOW_END_MAX_DAYS_OUT = 300
MAX_CREATES_PER_IP_PER_DAY = 5


def _iata(code: str, label: str) -> str:
    code = (code or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", code) or not hasattr(Airport, code):
        raise ValueError(f"unknown {label} airport: {code or '?'}")
    return code


def _parse_day(s: str) -> date:
    try:
        return date.fromisoformat((s or "").strip())
    except ValueError:
        raise ValueError(f"bad window date: {s}") from None


def create_watch(conn, email, origin, dest, window_start, window_end,
                 trip_nights, ceiling_usd=None, ip_hash=None, today=None):
    today = today or date.today()
    email = (email or "").strip().lower()
    if not email or len(email) > 254 or not EMAIL_RE.match(email):
        raise ValueError("invalid email")
    origin = _iata(origin, "origin")
    dest = _iata(dest, "destination")
    if origin == dest:
        raise ValueError("origin and destination must differ")
    nights = int(trip_nights)
    if not (NIGHTS_MIN <= nights <= NIGHTS_MAX):
        raise ValueError(f"nights must be {NIGHTS_MIN}-{NIGHTS_MAX}")
    ws, we = _parse_day(window_start), _parse_day(window_end)
    if ws < today + timedelta(days=1):
        raise ValueError("window must start tomorrow or later")
    if we <= ws:
        raise ValueError("window end must be after its start")
    if (we - ws).days > WINDOW_SPAN_MAX_DAYS:
        raise ValueError(f"window span is capped at {WINDOW_SPAN_MAX_DAYS} days")
    if (we - today).days > WINDOW_END_MAX_DAYS_OUT:
        raise ValueError(f"window may end at most {WINDOW_END_MAX_DAYS_OUT} days out")
    ceiling = int(ceiling_usd) if ceiling_usd not in (None, "", 0) else None

    # v1 cap: one live (pending/active/paused) watch per email
    live = conn.execute(
        "SELECT COUNT(*) FROM watches WHERE email=? AND status != 'deleted'",
        (email,)).fetchone()[0]
    if live:
        raise ValueError("one watch per email for now (more coming soon)")

    if ip_hash:
        n = conn.execute(
            "SELECT COUNT(*) FROM watches WHERE ip_hash=? AND created_at >= ?",
            (ip_hash, today.isoformat())).fetchone()[0]
        if n >= MAX_CREATES_PER_IP_PER_DAY:
            raise ValueError("too many watches created from this address today")

    token = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        """INSERT INTO watches (email, origin_iata, dest_iata, window_start,
               window_end, trip_nights, ceiling_usd, status, manage_token,
               ip_hash, created_at)
           VALUES (?,?,?,?,?,?,?, 'pending', ?, ?, ?)""",
        (email, origin, dest, ws.isoformat(), we.isoformat(), nights,
         ceiling, token, ip_hash, now))
    conn.commit()
    return {"id": cur.lastrowid, "manage_token": token}


def get_by_token(conn, token):
    row = conn.execute("SELECT * FROM watches WHERE manage_token=?",
                       ((token or "").strip(),)).fetchone()
    return dict(row) if row else None


def confirm_watch(conn, token) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "UPDATE watches SET status='active', confirmed_at=COALESCE(confirmed_at, ?) "
        "WHERE manage_token=? AND status IN ('pending','active')",
        (now, (token or "").strip()))
    conn.commit()
    return cur.rowcount > 0


def set_status(conn, token, status) -> bool:
    if status not in ("active", "paused", "deleted"):
        raise ValueError("bad status")
    cur = conn.execute(
        "UPDATE watches SET status=? WHERE manage_token=? AND status != 'deleted'",
        (status, (token or "").strip()))
    conn.commit()
    return cur.rowcount > 0


def active_watches(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM watches WHERE status='active' ORDER BY id").fetchall()
    return [dict(r) for r in rows]
```

Note: `conn.row_factory = sqlite3.Row` is required by `get_by_token`/`active_watches`; the runner and app set it (tests already do).

- [ ] **Step 2.4: Run, verify pass**
- [ ] **Step 2.5: Commit** `feat(watches): core domain — create/confirm/manage with validation + rate limit`

---

### Task 3: The brain — `server/watch_brain.py`

**Files:**
- Create: `server/watch_brain.py`
- Test: `tests/test_watch_brain.py`

- [ ] **Step 3.1: Failing tests**

`tests/test_watch_brain.py`:
```python
from datetime import date
from server.watch_brain import decide, DROP_FACTOR

T = date(2026, 6, 10)


def _series(*prices):
    """Build (iso_date, price) series ending yesterday."""
    from datetime import timedelta
    n = len(prices)
    return [((T - timedelta(days=n - i)).isoformat(), p)
            for i, p in enumerate(prices)]


def test_night_one_never_alerts():
    assert decide(series=[], today_best=500, ceiling=None,
                  last_alert_at=None, today=T) is None


def test_drop_trigger_fires_from_night_two():
    d = decide(series=_series(500), today_best=430, ceiling=None,
               last_alert_at=None, today=T)          # 430 <= 0.88*500=440
    assert d and d["trigger"] == "drop"


def test_no_drop_when_above_factor():
    assert decide(series=_series(500), today_best=460, ceiling=None,
                  last_alert_at=None, today=T) is None


def test_drop_uses_trailing_14_low_not_alltime():
    # old all-time low 300 (15+ nights ago) must NOT suppress today's alert
    prices = [300] + [500] * 15                       # 300 is outside trailing 14
    d = decide(series=_series(*prices), today_best=430, ceiling=None,
               last_alert_at=None, today=T)
    assert d and d["trigger"] == "drop"


def test_percentile_needs_14_nights():
    prices = list(range(400, 400 + 13))               # 13 nights
    assert decide(series=_series(*prices), today_best=399, ceiling=None,
                  last_alert_at=None, today=T) is None or \
           decide(series=_series(*prices), today_best=399, ceiling=None,
                  last_alert_at=None, today=T)["trigger"] != "percentile"


def test_percentile_fires_at_bottom_15():
    prices = [500 + i for i in range(20)]             # 20 nights, 500..519
    d = decide(series=_series(*prices), today_best=470, ceiling=None,
               last_alert_at=None, today=T)
    # 470 < all 20 -> bottom percentile; not a >=12% drop vs trailing low (500*.88=440)
    assert d and d["trigger"] == "percentile"


def test_ceiling_fires_anytime():
    d = decide(series=[], today_best=440, ceiling=450,
               last_alert_at=None, today=T)
    assert d and d["trigger"] == "ceiling"


def test_covenant_blocks_within_7_days():
    d = decide(series=_series(500), today_best=430, ceiling=None,
               last_alert_at=(T.replace(day=7)).isoformat(), today=T)  # 3 days ago
    assert d is None


def test_covenant_override_on_20pct_single_night_drop():
    d = decide(series=_series(500), today_best=395, ceiling=None,     # 395 < 0.8*500
               last_alert_at=(T.replace(day=7)).isoformat(), today=T)
    assert d and d["trigger"] == "drop" and d["override"] is True


def test_receipts_in_decision():
    prices = [500 + i for i in range(20)]
    d = decide(series=_series(*prices), today_best=470, ceiling=None,
               last_alert_at=None, today=T)
    assert d["nights_watched"] == 21                  # 20 prior + tonight
    assert 0 <= d["percentile"] <= 15
```

- [ ] **Step 3.2: Run, verify fail**

- [ ] **Step 3.3: Implement `server/watch_brain.py`**

```python
"""The alert brain: pure decision logic over a watch's nightly-best series.

Triggers (spec §7): drop >=12% vs trailing-14-night low (night 2+);
bottom-15% percentile (night 14+); user ceiling (anytime).
Covenant: <=1 alert / 7 days, overridden only by a >=20% single-night drop.
Reports observed history only — never forecasts.
"""
from datetime import date

DROP_FACTOR = 0.88        # today <= 88% of trailing low  => drop trigger
OVERRIDE_FACTOR = 0.80    # today <= 80% of trailing low  => covenant override
TRAIL_NIGHTS = 14
PCTL_MIN_NIGHTS = 14
PCTL_BOTTOM = 0.15
COVENANT_DAYS = 7


def decide(series, today_best, ceiling, last_alert_at, today: date):
    """series: [(iso_date, best_price)] prior nights (may be empty).
    Returns None or {trigger, override, nights_watched, percentile, trailing_low}.
    """
    if today_best is None:
        return None
    prior = [p for _, p in series if p is not None]
    trailing = prior[-TRAIL_NIGHTS:]
    trailing_low = min(trailing) if trailing else None

    trigger = None
    if ceiling and today_best < ceiling:
        trigger = "ceiling"
    if trailing_low is not None and today_best <= DROP_FACTOR * trailing_low:
        trigger = "drop"   # drop outranks ceiling for messaging
    pct = None
    if len(prior) >= PCTL_MIN_NIGHTS:
        below = sum(1 for p in prior if p < today_best)
        pct = round(100.0 * below / (len(prior) + 1), 1)
        if trigger is None and pct <= PCTL_BOTTOM * 100:
            trigger = "percentile"
    if trigger is None:
        return None

    override = (trailing_low is not None
                and today_best <= OVERRIDE_FACTOR * trailing_low)
    if last_alert_at:
        last_day = date.fromisoformat(last_alert_at[:10])
        if (today - last_day).days < COVENANT_DAYS and not override:
            return None

    return {
        "trigger": trigger,
        "override": override,
        "nights_watched": len(prior) + 1,
        "percentile": pct,
        "trailing_low": trailing_low,
    }


def nightly_best(conn, watch, observed_date: str):
    """Tonight's cheapest (price, depart, return) inside the watch window,
    from fare_observations written by the watch runner."""
    row = conn.execute(
        """SELECT total_price_usd, departure_date, return_date
           FROM fare_observations
           WHERE origin_iata=? AND dest_iata=? AND trip_nights=?
             AND source='watch' AND observed_date=?
             AND departure_date >= ? AND departure_date <= ?
             AND total_price_usd IS NOT NULL
           ORDER BY total_price_usd ASC LIMIT 1""",
        (watch["origin_iata"], watch["dest_iata"], watch["trip_nights"],
         observed_date, watch["window_start"], watch["window_end"])).fetchone()
    return (row[0], row[1], row[2]) if row else (None, None, None)


def series_for(conn, watch, before_date: str):
    """Prior nightly bests [(observed_date, best_price)], oldest first."""
    rows = conn.execute(
        """SELECT observed_date, MIN(total_price_usd)
           FROM fare_observations
           WHERE origin_iata=? AND dest_iata=? AND trip_nights=?
             AND source='watch' AND observed_date < ?
             AND departure_date >= ? AND departure_date <= ?
             AND total_price_usd IS NOT NULL
           GROUP BY observed_date ORDER BY observed_date""",
        (watch["origin_iata"], watch["dest_iata"], watch["trip_nights"],
         before_date, watch["window_start"], watch["window_end"])).fetchall()
    return [(r[0], r[1]) for r in rows]
```

- [ ] **Step 3.4: Run, verify pass**
- [ ] **Step 3.5: Commit** `feat(watches): alert brain — layered triggers + covenant (pure logic)`

---

### Task 4: Emails — `server/watch_emails.py`

**Files:**
- Create: `server/watch_emails.py`
- Test: `tests/test_watch_emails.py`

- [ ] **Step 4.1: Failing tests**

`tests/test_watch_emails.py`:
```python
import sqlite3
import pytest
from server.migrations import init_schema
from server import watch_emails


@pytest.fixture
def conn(temp_db_path):
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    c.row_factory = sqlite3.Row
    # curated destination for all-in enrichment
    c.execute("INSERT INTO destinations (iata, city, country, country_code, region, vibes, passport_required, visa_required_us, best_months, avg_daily_cost_usd, safety_tier, currency, lat, lng, base_catch, novelty_score) VALUES ('PLS','Providenciales','Turks and Caicos','TC','Caribbean','[\"beach\"]',1,0,'[12]',250,1,'USD',21.7,-72.2,NULL,3)")
    c.commit()
    yield c
    c.close()


WATCH = {"id": 1, "email": "a@b.co", "origin_iata": "BNA", "dest_iata": "PLS",
         "window_start": "2026-11-01", "window_end": "2027-01-31",
         "trip_nights": 7, "ceiling_usd": None, "manage_token": "tok123"}

DECISION = {"trigger": "drop", "override": False, "nights_watched": 47,
            "percentile": 8.0, "trailing_low": 410}


def test_alert_subject_and_receipts(conn):
    msg = watch_emails.compose_alert(
        conn, WATCH, DECISION, best=(325, "2026-12-09", "2026-12-16"),
        base_url="https://dashaway.io")
    assert msg["subject"].startswith("↓ $325")
    assert "Turks" in msg["subject"] or "Providenciales" in msg["subject"]
    assert "47 nights" in msg["html"]
    assert "Dec 9" in msg["html"]
    # all-in enrichment: 325 + 7*250 = 2075
    assert "2,075" in msg["html"]
    # google flights deep link + manage link present
    assert "google.com/travel/flights" in msg["html"]
    assert "manage?token=tok123" in msg["html"]
    assert "verify" in msg["text"].lower()


def test_alert_without_catalog_dest_skips_allin(conn):
    w = dict(WATCH, dest_iata="GRR")
    msg = watch_emails.compose_alert(conn, w, DECISION,
                                     best=(86, "2026-12-09", "2026-12-16"),
                                     base_url="https://dashaway.io")
    assert "all-in" not in msg["html"].lower()


def test_percentile_receipt_only_when_available(conn):
    d = dict(DECISION, percentile=None, nights_watched=3)
    msg = watch_emails.compose_alert(conn, WATCH, d,
                                     best=(325, "2026-12-09", "2026-12-16"),
                                     base_url="https://dashaway.io")
    assert "bottom" not in msg["html"].lower()


def test_pulse_lists_watches(conn):
    rows = [dict(WATCH, _best=(389, "2026-12-09", "2026-12-16"),
                 _nights=47, _trend="down")]
    msg = watch_emails.compose_pulse(rows, base_url="https://dashaway.io")
    assert "389" in msg["html"] and "47 nights" in msg["html"]
    assert "manage?token=tok123" in msg["html"]
```

- [ ] **Step 4.2: Run, verify fail**

- [ ] **Step 4.3: Implement `server/watch_emails.py`**

```python
"""Compose watch alert + weekly pulse emails (DashAway email palette).

All HTML inline (no stylesheets), matching server/digest.py conventions.
Honesty rules: observed history only; always 'prices move, verify before booking'.
"""
from datetime import datetime
from urllib.parse import quote

CREAM = "#f5f3ee"; CARD = "#ffffff"; BORDER = "#ece9e1"
INK = "#1a1a1f"; BODY = "#3a3a42"; MUTE = "#8a8a92"; ACCENT = "#a78bfa"
GREEN = "#0f7d64"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
SERIF = "Georgia,'Times New Roman',serif"


def _fmt_date(iso):
    return datetime.fromisoformat(iso).strftime("%b %-d")


def _dest_name(conn, iata):
    row = conn.execute(
        "SELECT city, country, avg_daily_cost_usd FROM destinations WHERE iata=?",
        (iata,)).fetchone()
    if row:
        return row[0], row[1], row[2]
    return iata, None, None


def gf_link(origin, dest, depart, ret):
    q = f"Flights from {origin} to {dest} on {depart} through {ret}"
    return "https://www.google.com/travel/flights?q=" + quote(q)


def compose_alert(conn, watch, decision, best, base_url):
    price, dep, ret = best
    city, country, daily = _dest_name(conn, watch["dest_iata"])
    place = city if not country else (country if "Turks" in (country or "") else city)
    manage = f"{base_url}/watch/manage?token={watch['manage_token']}"
    week = f"{_fmt_date(dep)}–{_fmt_date(ret)}"
    subject = f"↓ ${price:,.0f} — your {place} trip ({week})"

    receipts = []
    n = decision.get("nights_watched") or 0
    if n >= 2:
        receipts.append(f"lowest we've seen in {n} nights of watching"
                        if decision["trigger"] == "drop"
                        else f"{n} nights of watching")
    if decision.get("percentile") is not None:
        receipts.append(f"bottom {max(decision['percentile'], 1):.0f}% of everything we've observed")
    receipt_line = " · ".join(receipts)

    allin = ""
    if daily:
        total = price + watch["trip_nights"] * daily
        allin = (f'<p style="margin:14px 0 0;font:14px {SANS};color:{BODY}">'
                 f'${price:,.0f} flight → about <b>${total:,.0f} all-in</b> for '
                 f'the {watch["trip_nights"]}-night trip (flight + ~${daily}/day on the ground).</p>')

    link = gf_link(watch["origin_iata"], watch["dest_iata"], dep, ret)
    html = f"""<!doctype html><html><body style="margin:0;background:{CREAM};padding:24px 12px">
<div style="max-width:560px;margin:0 auto;background:{CARD};border:1px solid {BORDER};border-radius:12px;padding:28px">
  <p style="margin:0;font:600 11px {SANS};letter-spacing:.08em;color:{ACCENT}">DASHAWAY WATCH</p>
  <p style="margin:14px 0 0;font:italic 30px {SERIF};color:{INK}">${price:,.0f} to {city}.</p>
  <p style="margin:6px 0 0;font:15px {SANS};color:{BODY}">
    {watch['origin_iata']} → {watch['dest_iata']} · <b>{week}</b> · {watch['trip_nights']} nights</p>
  {f'<p style="margin:10px 0 0;font:13.5px {SANS};color:{GREEN}"><b>{receipt_line}</b></p>' if receipt_line else ''}
  {allin}
  <p style="margin:22px 0 0"><a href="{link}"
     style="display:inline-block;background:{ACCENT};color:#fff;text-decoration:none;font:600 15px {SANS};padding:12px 22px;border-radius:8px">
     See it on Google Flights</a></p>
  <p style="margin:18px 0 0;font:12px {SANS};color:{MUTE}">Prices move — verify before booking.
     We report what we observed; we never predict.</p>
  <p style="margin:16px 0 0;font:12px {SANS};color:{MUTE}">
     <a href="{manage}" style="color:{MUTE}">Pause or manage this watch</a></p>
</div></body></html>"""

    text = (f"${price:,.0f} — {watch['origin_iata']} to {watch['dest_iata']}, {week}, "
            f"{watch['trip_nights']} nights.\n"
            + (receipt_line + "\n" if receipt_line else "")
            + f"See it: {link}\nPrices move - verify before booking.\nManage: {manage}\n")
    return {"subject": subject, "html": html, "text": text}


def compose_pulse(rows, base_url):
    """rows: watch dicts each with _best=(price,dep,ret)|None, _nights, _trend."""
    items = []
    for w in rows:
        manage = f"{base_url}/watch/manage?token={w['manage_token']}"
        if w.get("_best") and w["_best"][0] is not None:
            p, dep, ret = w["_best"]
            arrow = {"down": "↓", "up": "↑"}.get(w.get("_trend"), "→")
            line = (f"best week {_fmt_date(dep)}–{_fmt_date(ret)} at "
                    f"<b>${p:,.0f}</b> · trending {arrow}")
        else:
            line = "no fares observed this week"
        items.append(
            f'<div style="padding:14px 0;border-bottom:1px solid {BORDER}">'
            f'<p style="margin:0;font:600 15px {SANS};color:{INK}">'
            f'{w["origin_iata"]} → {w["dest_iata"]}</p>'
            f'<p style="margin:4px 0 0;font:13.5px {SANS};color:{BODY}">'
            f'Watched {w.get("_nights", 0)} nights · {line}</p>'
            f'<p style="margin:4px 0 0;font:12px {SANS}">'
            f'<a href="{manage}" style="color:{MUTE}">manage</a></p></div>')
    html = f"""<!doctype html><html><body style="margin:0;background:{CREAM};padding:24px 12px">
<div style="max-width:560px;margin:0 auto;background:{CARD};border:1px solid {BORDER};border-radius:12px;padding:28px">
  <p style="margin:0;font:600 11px {SANS};letter-spacing:.08em;color:{ACCENT}">DASHAWAY WATCH · WEEKLY PULSE</p>
  <p style="margin:12px 0 8px;font:italic 24px {SERIF};color:{INK}">Still watching.</p>
  {''.join(items)}
  <p style="margin:18px 0 0;font:12px {SANS};color:{MUTE}">We email alerts only when something is decision-worthy. Prices move — verify before booking.</p>
</div></body></html>"""
    text = "\n".join(
        f"{w['origin_iata']}->{w['dest_iata']}: watched {w.get('_nights',0)} nights"
        for w in rows)
    return {"subject": "Your watches · weekly pulse", "html": html, "text": text}
```

- [ ] **Step 4.4: Run, verify pass**
- [ ] **Step 4.5: Commit** `feat(watches): alert + pulse email composition (DashAway palette, all-in enrichment)`

---

### Task 5: Nightly runner — `server/watch_runner.py`

**Files:**
- Create: `server/watch_runner.py`
- Test: `tests/test_watch_runner.py`

- [ ] **Step 5.1: Failing tests**

`tests/test_watch_runner.py`:
```python
from datetime import date
import sqlite3
from unittest.mock import patch, MagicMock
import pytest
from server.migrations import init_schema
from server import watches, watch_runner


class FakeResult:
    def __init__(self, dep, ret, price):
        self.origin_iata = "BNA"; self.dest_iata = "PLS"
        self.departure_date = dep; self.return_date = ret
        self.trip_nights = 7; self.total_price_usd = price
        self.stops = 0; self.carrier_codes = ["G4"]


class FakeFli:
    def __init__(self, results=None, raises=None):
        self.results = results or []
        self.raises = raises
        self.calls = []

    def search_dates(self, origin, dest, start_date, end_date, trip_nights):
        self.calls.append((origin, dest, start_date, end_date, trip_nights))
        if self.raises:
            raise self.raises
        return self.results


@pytest.fixture
def conn(temp_db_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", temp_db_path)
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _watch(conn, email="a@b.co", dest="PLS"):
    w = watches.create_watch(conn, email=email, origin="BNA", dest=dest,
                             window_start="2026-11-01", window_end="2027-01-31",
                             trip_nights=7, today=date(2026, 6, 10))
    watches.confirm_watch(conn, w["manage_token"])
    return w


def test_scan_writes_watch_observations(conn):
    _watch(conn)
    fli = FakeFli([FakeResult("2026-12-09", "2026-12-16", 325),
                   FakeResult("2026-11-04", "2026-11-11", 460)])
    with patch.object(watch_runner.email_client, "send_digest_email") as send:
        summary = watch_runner.run(conn, fli=fli, sleep_s=0,
                                   today=date(2026, 6, 10), base_url="http://x")
    assert len(fli.calls) == 1
    rows = conn.execute("SELECT source, COUNT(*) FROM fare_observations GROUP BY source").fetchall()
    assert dict(rows)["watch"] == 2
    assert summary["scanned"] == 1 and summary["errors"] == 0


def test_dedupe_same_route_window(conn):
    _watch(conn, email="a@b.co")
    _watch(conn, email="b@c.co")          # same route+window+nights
    fli = FakeFli([FakeResult("2026-12-09", "2026-12-16", 325)])
    with patch.object(watch_runner.email_client, "send_digest_email"):
        watch_runner.run(conn, fli=fli, sleep_s=0, today=date(2026, 6, 10),
                         base_url="http://x")
    assert len(fli.calls) == 1            # one request serves both watches


def test_alert_sent_and_logged_on_trigger(conn):
    w = _watch(conn)
    # seed a prior night at 500 so tonight's 325 is a >=12% drop
    conn.execute("INSERT INTO fare_observations (origin_iata,dest_iata,departure_date,return_date,trip_nights,total_price_usd,source,observed_date,fetched_at) VALUES ('BNA','PLS','2026-12-09','2026-12-16',7,500,'watch','2026-06-09','x')")
    conn.commit()
    fli = FakeFli([FakeResult("2026-12-09", "2026-12-16", 325)])
    with patch.object(watch_runner.email_client, "send_digest_email") as send:
        summary = watch_runner.run(conn, fli=fli, sleep_s=0,
                                   today=date(2026, 6, 10), base_url="http://x")
    assert summary["alerts"] == 1
    assert send.call_count >= 1
    ev = conn.execute("SELECT kind, trigger, best_price FROM watch_events").fetchone()
    assert ev["kind"] == "alert" and ev["trigger"] == "drop" and ev["best_price"] == 325
    la = conn.execute("SELECT last_alert_at FROM watches").fetchone()[0]
    assert la is not None


def test_plausibility_guard_filters_garbage(conn):
    _watch(conn)
    fli = FakeFli([FakeResult("2026-12-09", "2026-12-16", 7000),   # implausible
                   FakeResult("2026-12-10", "2026-12-17", 410)])
    with patch.object(watch_runner.email_client, "send_digest_email"):
        watch_runner.run(conn, fli=fli, sleep_s=0, today=date(2026, 6, 10),
                         base_url="http://x")
    prices = [r[0] for r in conn.execute(
        "SELECT total_price_usd FROM fare_observations WHERE source='watch'")]
    assert prices == [410]


def test_429_aborts_night(conn):
    _watch(conn, email="a@b.co", dest="PLS")
    _watch(conn, email="b@c.co", dest="GRR")
    fli = FakeFli(raises=RuntimeError("HTTP 429 rate-limited"))
    with patch.object(watch_runner.email_client, "send_digest_email") as send:
        summary = watch_runner.run(conn, fli=fli, sleep_s=0,
                                   today=date(2026, 6, 10), base_url="http://x")
    assert summary["aborted_429"] is True
    assert len(fli.calls) == 1            # stopped immediately, no second route
    assert send.call_count == 1           # the ops alert email


def test_non_429_error_skips_route_and_continues(conn):
    _watch(conn, email="a@b.co", dest="PLS")
    _watch(conn, email="b@c.co", dest="GRR")
    calls = {"n": 0}
    class Flaky(FakeFli):
        def search_dates(self, *a, **k):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            return [FakeResult("2026-12-09", "2026-12-16", 325)]
    with patch.object(watch_runner.email_client, "send_digest_email"):
        summary = watch_runner.run(conn, fli=Flaky(), sleep_s=0,
                                   today=date(2026, 6, 10), base_url="http://x")
    assert summary["errors"] == 1 and summary["scanned"] == 2
```

- [ ] **Step 5.2: Run, verify fail**

- [ ] **Step 5.3: Implement `server/watch_runner.py`**

```python
"""Nightly watch scan: one paced SearchDates request per distinct watched route.

Spec rules honored here:
- pacing between requests (politeness; shares the warmed IP with the refresh)
- plausibility guard reused from price_refresh
- ANY 429 aborts the entire night (never retry into a block) + ops alert
- alerts via watch_brain decisions; covenant enforced via last_alert_at
- ops summary email at the end of every run
"""
import json
import logging
import os
import sqlite3
import time
from datetime import date, datetime, timezone

from server import email_client, watches, watch_brain, watch_emails
from server.price_refresh import _plausible

log = logging.getLogger("watch_runner")

SLEEP_BETWEEN_CALLS = 6.0
RUNTIME_TRIPWIRE_S = 3 * 3600
ERROR_RATE_TRIPWIRE = 0.10


def _is_429(err) -> bool:
    m = str(err).lower()
    return "429" in m or "rate-limit" in m or "rate limit" in m


def _ops_email(subject: str, body: str) -> None:
    to = os.environ.get("OPS_EMAIL") or os.environ.get("RESEND_REPLY_TO")
    if not to:
        log.warning("no OPS_EMAIL configured; ops note: %s", subject)
        return
    email_client.send_digest_email(to, subject, f"<pre>{body}</pre>", body)


def run(conn, fli=None, sleep_s: float = SLEEP_BETWEEN_CALLS,
        today: date | None = None, base_url: str = "https://dashaway.io") -> dict:
    today = today or date.today()
    observed = today.isoformat()
    fetched_at = datetime.now(timezone.utc).isoformat()
    if fli is None:
        from server.fli_client import FliClient
        fli = FliClient()

    active = watches.active_watches(conn)
    groups: dict[tuple, list[dict]] = {}
    for w in active:
        key = (w["origin_iata"], w["dest_iata"], w["window_start"],
               w["window_end"], w["trip_nights"])
        groups.setdefault(key, []).append(w)

    t0 = time.monotonic()
    summary = {"watches": len(active), "routes": len(groups), "scanned": 0,
               "errors": 0, "alerts": 0, "aborted_429": False}

    for i, ((origin, dest, ws, we, nights), members) in enumerate(groups.items()):
        try:
            results = fli.search_dates(origin, dest,
                                       date.fromisoformat(ws),
                                       date.fromisoformat(we), nights)
        except Exception as e:
            if _is_429(e):
                summary["aborted_429"] = True
                log.error("429 from Google on %s->%s; ABORTING the night", origin, dest)
                _ops_email("WATCHES: 429 — night aborted",
                           f"429 on {origin}->{dest} after {summary['scanned']} routes. "
                           f"Job stopped to protect the IP. {e}")
                break
            summary["errors"] += 1
            summary["scanned"] += 1
            log.warning("%s->%s scan error (skipping route): %s", origin, dest, e)
            continue

        kept = [r for r in (results or []) if _plausible(r.total_price_usd)]
        for r in kept:
            conn.execute(
                """INSERT OR REPLACE INTO fare_observations
                   (origin_iata, dest_iata, departure_date, return_date,
                    trip_nights, total_price_usd, stops, carrier_codes,
                    source, observed_date, fetched_at)
                   VALUES (?,?,?,?,?,?,?,?, 'watch', ?, ?)""",
                (r.origin_iata, r.dest_iata, r.departure_date, r.return_date,
                 r.trip_nights, r.total_price_usd, r.stops,
                 json.dumps(r.carrier_codes) if r.carrier_codes else None,
                 observed, fetched_at))
        conn.commit()
        summary["scanned"] += 1

        for w in members:
            best = watch_brain.nightly_best(conn, w, observed)
            if best[0] is None:
                continue
            series = watch_brain.series_for(conn, w, observed)
            decision = watch_brain.decide(
                series, best[0], w["ceiling_usd"], w["last_alert_at"], today)
            if not decision:
                continue
            msg = watch_emails.compose_alert(conn, w, decision, best, base_url)
            manage = f"{base_url}/watch/manage?token={w['manage_token']}"
            email_client.send_digest_email(
                w["email"], msg["subject"], msg["html"], msg["text"],
                unsubscribe_url=manage)
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO watch_events (watch_id, kind, sent_at, best_price,"
                " best_depart, best_return, trigger) VALUES (?,?,?,?,?,?,?)",
                (w["id"], "alert", now, best[0], best[1], best[2],
                 decision["trigger"]))
            conn.execute("UPDATE watches SET last_alert_at=? WHERE id=?",
                         (now, w["id"]))
            conn.commit()
            summary["alerts"] += 1

        if i + 1 < len(groups) and sleep_s:
            time.sleep(sleep_s)

    runtime = time.monotonic() - t0
    summary["runtime_s"] = round(runtime)
    tripwires = []
    if runtime > RUNTIME_TRIPWIRE_S:
        tripwires.append(f"runtime {runtime/3600:.1f}h > 3h")
    if summary["scanned"] and summary["errors"] / summary["scanned"] > ERROR_RATE_TRIPWIRE:
        tripwires.append(f"error rate {summary['errors']}/{summary['scanned']}")
    body = json.dumps(summary, indent=2)
    subject = ("WATCHES tripwire: " + "; ".join(tripwires)) if tripwires else \
              (f"watches nightly: {summary['scanned']} routes, "
               f"{summary['alerts']} alerts")
    if not summary["aborted_429"]:        # 429 already sent its own ops email
        _ops_email(subject, body)
    log.info("watch run done: %s", summary)
    return summary


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    db_path = os.environ.get("DATABASE_PATH", "./teaser.dev.sqlite")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        run(conn)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5.4: Run, verify pass** (note: ops email in tests is captured by the same `send_digest_email` patch)
- [ ] **Step 5.5: Run the FULL suite** (`python -m pytest -q`) — no regressions
- [ ] **Step 5.6: Commit** `feat(watches): nightly runner — paced scan, abort-on-429, alerts, ops summary`

---

### Task 6: API endpoints in `server/app.py`

**Files:**
- Modify: `server/app.py`
- Test: `tests/test_watch_endpoints.py`

- [ ] **Step 6.1: Failing tests**

`tests/test_watch_endpoints.py`:
```python
from unittest.mock import patch


def _create(client, **over):
    body = {"email": "a@b.co", "origin": "BNA", "dest": "PLS",
            "window_start": "2026-11-01", "window_end": "2027-01-31",
            "nights": 7, "ceiling": 450}
    body.update(over)
    with patch("server.app.watch_emails.send_watch_confirm", return_value={"id": "m"}) as s:
        resp = client.post("/api/watch", json=body,
                           headers={"Accept": "application/json"})
    return resp, s


def test_create_watch_sends_confirm(client):
    resp, send = _create(client)
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "pending"
    assert send.call_count == 1


def test_create_watch_validation_400(client):
    resp, _ = _create(client, origin="QQQ")
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
    r = client.post("/watch/manage", data={"token": token, "action": "delete"})
    assert conn.execute("SELECT status FROM watches").fetchone()[0] == "deleted"


def test_manage_bad_token_404(client):
    assert client.get("/watch/manage?token=zzz").status_code == 404
    assert client.post("/watch/manage", data={"token": "zzz", "action": "pause"}).status_code == 404
```

- [ ] **Step 6.2: Run, verify fail**

- [ ] **Step 6.3: Implement.**

(a) Add to `server/watch_emails.py` (confirm email + sender helpers used by the app):

```python
def send_watch_confirm(email, watch, confirm_url):
    """Double opt-in: watch is pending until this link is clicked."""
    from server import email_client
    html = f"""<!doctype html><html><body style="margin:0;background:{CREAM};padding:24px 12px">
<div style="max-width:560px;margin:0 auto;background:{CARD};border:1px solid {BORDER};border-radius:12px;padding:28px">
  <p style="margin:0;font:600 11px {SANS};letter-spacing:.08em;color:{ACCENT}">DASHAWAY WATCH</p>
  <p style="margin:12px 0 0;font:italic 26px {SERIF};color:{INK}">Confirm your watch.</p>
  <p style="margin:10px 0 0;font:15px {SANS};color:{BODY}">
    {watch['origin_iata']} → {watch['dest_iata']} ·
    {_fmt_date(watch['window_start'])} – {_fmt_date(watch['window_end'])} ·
    {watch['trip_nights']} nights</p>
  <p style="margin:20px 0 0"><a href="{confirm_url}"
     style="display:inline-block;background:{ACCENT};color:#fff;text-decoration:none;font:600 15px {SANS};padding:12px 22px;border-radius:8px">
     Start watching</a></p>
  <p style="margin:16px 0 0;font:12px {SANS};color:{MUTE}">We'll check it every night and
     email only when something is decision-worthy. If you didn't request this, ignore it.</p>
</div></body></html>"""
    text = (f"Confirm your DashAway watch: {watch['origin_iata']} -> "
            f"{watch['dest_iata']}, {watch['window_start']} to "
            f"{watch['window_end']}, {watch['trip_nights']} nights.\n"
            f"Confirm: {confirm_url}\nIf you didn't request this, ignore it.\n")
    return email_client.send_digest_email(
        email, "Confirm your DashAway watch", html, text)
```

(b) In `server/app.py` — add imports near the top (`from server import watches as watches_mod`, `from server import watch_emails`) and these routes inside `create_app()` (following the `/api/signup` and `/unsubscribe` patterns; reuse `_hash_ip` and the JSON/form duality):

```python
    @app.route("/api/watch", methods=["POST"])
    def create_watch():
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        ip_hash = _hash_ip(ip.split(",")[0].strip()) if ip else None
        conn = _db()                      # use the app's existing connection helper
        try:
            w = watches_mod.create_watch(
                conn,
                email=data.get("email"),
                origin=data.get("origin"),
                dest=data.get("dest"),
                window_start=data.get("window_start"),
                window_end=data.get("window_end"),
                trip_nights=data.get("nights") or 7,
                ceiling_usd=data.get("ceiling"),
                ip_hash=ip_hash,
            )
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        row = watches_mod.get_by_token(conn, w["manage_token"])
        base = request.host_url.rstrip("/")
        confirm_url = f"{base}/watch/confirm?token={w['manage_token']}"
        watch_emails.send_watch_confirm(row["email"], row, confirm_url)
        return jsonify({"status": "pending",
                        "message": "check your email to confirm"})

    @app.route("/watch/confirm")
    def watch_confirm():
        conn = _db()
        ok = watches_mod.confirm_watch(conn, request.args.get("token", ""))
        page = _watch_page(
            "You're watching." if ok else "Link not found.",
            "We'll price this trip every night and email you when it's time "
            "to book. First pulse arrives Sunday." if ok else
            "This confirmation link is invalid or the watch was deleted.")
        return (page, 200 if ok else 404)

    @app.route("/watch/manage", methods=["GET", "POST"])
    def watch_manage():
        conn = _db()
        token = (request.args.get("token") or request.form.get("token") or "").strip()
        row = watches_mod.get_by_token(conn, token)
        if not row or row["status"] == "deleted":
            return (_watch_page("Not found.", "This manage link is invalid."), 404)
        if request.method == "POST":
            action = request.form.get("action", "")
            new = {"pause": "paused", "resume": "active",
                   "delete": "deleted"}.get(action)
            if not new:
                return (_watch_page("Unknown action.", ""), 400)
            watches_mod.set_status(conn, token, new)
            row = watches_mod.get_by_token(conn, token)
        status = row["status"]
        body = (f"{row['origin_iata']} → {row['dest_iata']} · "
                f"{row['window_start']} to {row['window_end']} · "
                f"{row['trip_nights']} nights · status: {status}")
        actions = "".join(
            f'<form method="POST" style="display:inline">'
            f'<input type="hidden" name="token" value="{token}">'
            f'<button name="action" value="{a}">{label}</button></form> '
            for a, label in (
                [("pause", "Pause"), ("delete", "Delete")] if status == "active"
                else [("resume", "Resume"), ("delete", "Delete")] if status == "paused"
                else []))
        return _watch_page("Your watch", body + "<br><br>" + actions)
```

…plus a small `_watch_page(title, body)` helper styled like `_unsub_page` (same minimal inline-styled HTML shell; copy that function's structure and palette).

- [ ] **Step 6.4: Run new tests + FULL suite, verify pass**
- [ ] **Step 6.5: Commit** `feat(watches): API — create (double opt-in), confirm, manage`

---

### Task 7: The /watch page (static) + nginx

**Files:**
- Create: `public/watch.html`
- Modify: `public/styles.css` only if a class is missing (prefer reuse)
- Modify: `deploy/nginx-dashaway.conf`

- [ ] **Step 7.1: Create `public/watch.html`** — DashAway site style (NOT the email palette): site CSS vars, Instrument Serif headline, the form mirrors flights.distillworks.com learnings. Fields: From (one airport), To (one airport), "Anytime between" (two date inputs), Nights (number, default 7), "Alert me under $___ (optional)", Email. JS: fetch POST `/api/watch` (with `Accept: application/json`), success state swaps the form for "Check your email to confirm." Inline errors from the API's `error` string. Include honest subcopy: "We check your trip every night and email only when it's decision-worthy. No spam; one watch per email for now." Form has `action="/api/watch" method="POST"` no-JS fallback (the endpoint already accepts form-encoded).

- [ ] **Step 7.2: nginx** — add to the dashaway.io server block (mirroring existing exact-match locations):

```nginx
    location = /watch { try_files /watch.html =404; }
    location ^~ /watch/ {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 10s;
    }
```

(`/api/watch` is already covered by the existing `/api/` proxy block. NOTE: the hub regex `^/([a-z][a-z-]*[a-z])$` would also match `/watch` — the exact-match `location = /watch` wins in nginx precedence, and `^~ /watch/` beats regexes for the subpaths. Verify with curl after deploy.)

- [ ] **Step 7.3: Browser test locally** (flask dev server + the page): create a watch end-to-end with email mocked/env unset (email send fails soft by design); verify row lands `pending`.
- [ ] **Step 7.4: Commit** `feat(watches): /watch page + nginx routes`

---

### Task 8: Weekly pulse — `server/watch_pulse.py`

**Files:**
- Create: `server/watch_pulse.py`
- Test: `tests/test_watch_pulse.py`

- [ ] **Step 8.1: Failing tests**

`tests/test_watch_pulse.py`:
```python
from datetime import date
import sqlite3
from unittest.mock import patch
import pytest
from server.migrations import init_schema
from server import watches, watch_pulse


@pytest.fixture
def conn(temp_db_path):
    init_schema(temp_db_path)
    c = sqlite3.connect(temp_db_path)
    c.row_factory = sqlite3.Row
    yield c
    c.close()


def _seed(conn, email="a@b.co"):
    w = watches.create_watch(conn, email=email, origin="BNA", dest="PLS",
                             window_start="2026-11-01", window_end="2027-01-31",
                             trip_nights=7, today=date(2026, 6, 10))
    watches.confirm_watch(conn, w["manage_token"])
    for day, price in (("2026-06-08", 500), ("2026-06-09", 460)):
        conn.execute("INSERT INTO fare_observations (origin_iata,dest_iata,departure_date,return_date,trip_nights,total_price_usd,source,observed_date,fetched_at) VALUES ('BNA','PLS','2026-12-09','2026-12-16',7,?,'watch',?,'x')", (price, day))
    conn.commit()
    return w


def test_pulse_sends_one_email_per_user(conn):
    _seed(conn, "a@b.co")
    with patch("server.watch_pulse.email_client.send_digest_email") as send:
        n = watch_pulse.send_pulses(conn, base_url="http://x",
                                    today=date(2026, 6, 10))
    assert n == 1 and send.call_count == 1
    args = send.call_args[0]
    assert args[0] == "a@b.co"
    assert "pulse" in args[1].lower()
    ev = conn.execute("SELECT COUNT(*) FROM watch_events WHERE kind='pulse'").fetchone()[0]
    assert ev == 1


def test_pulse_idempotent_same_day(conn):
    _seed(conn)
    with patch("server.watch_pulse.email_client.send_digest_email") as send:
        watch_pulse.send_pulses(conn, base_url="http://x", today=date(2026, 6, 10))
        n2 = watch_pulse.send_pulses(conn, base_url="http://x", today=date(2026, 6, 10))
    assert n2 == 0 and send.call_count == 1


def test_pulse_skips_paused(conn):
    w = _seed(conn)
    watches.set_status(conn, w["manage_token"], "paused")
    with patch("server.watch_pulse.email_client.send_digest_email") as send:
        n = watch_pulse.send_pulses(conn, base_url="http://x", today=date(2026, 6, 10))
    assert n == 0 and send.call_count == 0
```

- [ ] **Step 8.2: Run, verify fail**

- [ ] **Step 8.3: Implement `server/watch_pulse.py`**

```python
"""Weekly pulse: one Sunday email per user listing their active watches.
Idempotent per (watch, day) via watch_events kind='pulse'."""
import logging
import os
import sqlite3
import time
from datetime import date, datetime, timezone

from server import email_client, watches, watch_brain, watch_emails

log = logging.getLogger("watch_pulse")
SLEEP_BETWEEN_SENDS = 0.4


def _trend(series):
    if len(series) < 4:
        return "flat"
    half = len(series) // 2
    a = sum(p for _, p in series[:half]) / half
    b = sum(p for _, p in series[half:]) / (len(series) - half)
    return "down" if b < a * 0.97 else ("up" if b > a * 1.03 else "flat")


def send_pulses(conn, base_url: str, today: date | None = None) -> int:
    today = today or date.today()
    cutoff = today.isoformat()
    by_email: dict[str, list[dict]] = {}
    for w in watches.active_watches(conn):
        sent = conn.execute(
            "SELECT 1 FROM watch_events WHERE watch_id=? AND kind='pulse' "
            "AND sent_at >= ?", (w["id"], cutoff)).fetchone()
        if sent:
            continue
        series = watch_brain.series_for(conn, w, (today.isoformat()) + "z")
        # series_for is strictly-before; append nothing — pulse reports history
        w = dict(w)
        w["_nights"] = len(series)
        if series:
            best_day, best_price = min(series, key=lambda t: t[1])
            best = watch_brain.nightly_best(conn, w, series[-1][0])
            w["_best"] = best if best[0] is not None else (best_price, w["window_start"], w["window_end"])
            w["_trend"] = _trend(series)
        else:
            w["_best"] = None
            w["_trend"] = "flat"
        by_email.setdefault(w["email"], []).append(w)

    sent_users = 0
    now = datetime.now(timezone.utc).isoformat()
    for email_addr, rows in by_email.items():
        msg = watch_emails.compose_pulse(rows, base_url=base_url)
        manage = f"{base_url}/watch/manage?token={rows[0]['manage_token']}"
        email_client.send_digest_email(email_addr, msg["subject"], msg["html"],
                                       msg["text"], unsubscribe_url=manage)
        for w in rows:
            conn.execute(
                "INSERT INTO watch_events (watch_id, kind, sent_at) VALUES (?,?,?)",
                (w["id"], "pulse", now))
        conn.commit()
        sent_users += 1
        time.sleep(SLEEP_BETWEEN_SENDS)
    log.info("pulse: %d user emails sent", sent_users)
    return sent_users


def main() -> int:
    logging.basicConfig(level=logging.INFO)
    db_path = os.environ.get("DATABASE_PATH", "./teaser.dev.sqlite")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        send_pulses(conn, base_url=os.environ.get("BASE_URL", "https://dashaway.io"))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 8.4: Run, verify pass; full suite green**
- [ ] **Step 8.5: Commit** `feat(watches): weekly pulse sender (idempotent per day)`

---

### Task 9: systemd units

**Files:**
- Create: `deploy/promptiv-watches.service`, `deploy/promptiv-watches.timer`
- Create: `deploy/promptiv-watch-pulse.service`, `deploy/promptiv-watch-pulse.timer`

- [ ] **Step 9.1: Write units** (templates = `promptiv-refresh.*`):

`deploy/promptiv-watches.service`:
```ini
[Unit]
Description=DashAway Watches nightly scan
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=www-data
Group=www-data
WorkingDirectory=/srv/promptiv
Environment=DATABASE_PATH=/var/lib/promptiv/teaser.sqlite
EnvironmentFile=/srv/promptiv/.env
ExecStart=/srv/promptiv/.venv/bin/python -m server.watch_runner
StandardOutput=append:/var/log/promptiv/watches.log
StandardError=append:/var/log/promptiv/watches.log
TimeoutSec=14400

[Install]
WantedBy=multi-user.target
```

`deploy/promptiv-watches.timer`:
```ini
[Unit]
Description=Trigger DashAway Watches scan nightly at 03:00 UTC (finishes before the 07:00 refresh)

[Timer]
OnCalendar=*-*-* 03:00:00 UTC
Persistent=true
RandomizedDelaySec=600

[Install]
WantedBy=timers.target
```

`deploy/promptiv-watch-pulse.service` (ExecStart `-m server.watch_pulse`, log `watch-pulse.log`, TimeoutSec 1800; otherwise identical) and `deploy/promptiv-watch-pulse.timer` (`OnCalendar=Sun *-*-* 15:00:00 UTC` — 10:00 CT, mirrors the digest's Sunday cadence without colliding with it).

- [ ] **Step 9.2: Commit** `feat(watches): systemd units (nightly 03:00 UTC scan + Sunday pulse)`

---

### Task 10: Deploy + live verification

- [ ] **Step 10.1: Full local suite green** (`python -m pytest -q`)
- [ ] **Step 10.2: rsync** (the standard incremental deploy command from DEPLOY.md; excludes .env/sqlite)
- [ ] **Step 10.3: On the server:** run the migration one-liner (init_schema), install + enable the 4 unit files (`cp deploy/promptiv-watch* /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now promptiv-watches.timer promptiv-watch-pulse.timer`), copy nginx config + `nginx -t` + reload, `systemctl restart promptiv.service`. Add `OPS_EMAIL` to `/srv/promptiv/.env` (ask Adam which address; default to RESEND_REPLY_TO behavior if unset).
- [ ] **Step 10.4: Live smoke (end-to-end with a real email Adam owns):**
  1. `curl -s https://dashaway.io/watch | grep -c watch-form` → page serves.
  2. Create a real watch via the page (Adam's test email; e.g. BNA→PLS Nov–Jan, 7 nights).
  3. Confirm via the email link → manage page shows `active`; pause/resume round-trip works.
  4. Trigger one manual scan: `systemctl start promptiv-watches.service`; verify `fare_observations` gains `source='watch'` rows for the route, log shows pacing, ops summary email arrives.
  5. Confirm nginx regex precedence: `/watch`, `/watch/confirm?token=x` (404), `/nashville` all behave.
- [ ] **Step 10.5: Watch the first 3 nightly runs** (logs + ops emails) for runtime, errors, and any 429.
- [ ] **Step 10.6: Commit any deploy fixes; update `docs/ARCHITECTURE.md`** (new section: Watches — model, timers, brain constants) **and memory** (`project_promptiv.md`: Watches LIVE status, ops commands).

---

### Task 11 (follow-on, explicitly deferred until validation): /watch CTA placement

Add the /watch link to the homepage nav + hub pages + digest footer (the funnel). Hold until the first manual end-to-end watch has survived ~a week of nightly runs cleanly — don't invite traffic onto an unproven nightly job.

---

## Self-review notes (resolved during planning)

- `fare_observations.source='watch'` is safe: the UNIQUE key includes `source` (verified in migrations.py), so watch rows never collide with refresh rows, and `INSERT OR REPLACE` keeps same-night re-runs idempotent.
- The brain derives the series from `fare_observations` instead of a new table — one source of truth; window edits via manage automatically re-scope history. Tradeoff accepted: percentile resets if the user changes the route (correct behavior anyway).
- nginx: `location = /watch` (exact) outranks the hub regex; `^~ /watch/` outranks regexes for subpaths. Step 10.4.5 verifies this live.
- The ops email reuses `send_digest_email` (no new sender plumbing). If `OPS_EMAIL`/`RESEND_REPLY_TO` are both unset, the runner logs a warning instead of failing — the scan itself must never depend on email.
- `watch_runner` takes `conn` + injected `fli` so every test runs offline; `FLI_MOCK=1` additionally allows a full server-side dry run before the first real scan.
- The drop trigger compares against the trailing-14 low of PRIOR nights only (today's price is not in its own baseline).
- Pulse idempotency keys on `watch_events(kind='pulse', sent_at >= today)` — re-running the Sunday service is safe.
