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
    ceiling = int(ceiling_usd) if ceiling_usd not in (None, "", 0, "0") else None

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
