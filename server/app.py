"""Promptiv teaser Flask app."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, make_response, redirect, request, send_from_directory

from server import catch as catchmod
from server import db, email_client
from server import ranking as rankmod
from server.migrations import init_schema


# Pragmatic email regex — not RFC-strict but rejects obvious junk.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SESSION_COOKIE_NAME = "promptiv_session"
VALID_TRIP_NIGHTS = {5, 7, 10}


def _get_or_create_session_id(req, resp, is_dev: bool) -> str:
    sid = req.cookies.get(SESSION_COOKIE_NAME)
    if not sid:
        sid = secrets.token_hex(16)
        resp.set_cookie(
            SESSION_COOKIE_NAME, sid,
            max_age=60 * 60 * 24 * 30,  # 30 days
            httponly=True,
            samesite="Lax",
            secure=not is_dev,
        )
    return sid


def _google_flights_url(origin: str, dest_city: str) -> str:
    q = f"Flights to {dest_city} from {origin}"
    return f"https://www.google.com/travel/flights?q={urllib.parse.quote(q)}"


def _hash_ip(ip: Optional[str]) -> Optional[str]:
    if not ip:
        return None
    secret = os.environ.get("SECRET_KEY", "")
    if not secret:
        # SECRET_KEY missing — refuse to fall back to unsalted hash silently.
        # Returning None means we record no IP rather than a weakly hashed one.
        return None
    return hmac.new(
        secret.encode("utf-8"),
        ip.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


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

    @app.route("/thanks.html")
    @app.route("/thanks")
    def thanks_page():
        return send_from_directory(str(public_dir), "thanks.html")

    @app.route("/api/healthz")
    def healthz():
        import sqlite3
        snapshot_count = 0
        last_refresh_at = None
        db_status = "ok"
        if db_path:
            try:
                conn = sqlite3.connect(db_path)
                try:
                    row = conn.execute(
                        "SELECT COUNT(*), MAX(fetched_at) FROM price_snapshots"
                    ).fetchone()
                    snapshot_count = row[0] or 0
                    last_refresh_at = row[1]
                finally:
                    conn.close()
            except sqlite3.Error as e:
                db_status = f"error: {e}"
        return jsonify({
            "status": "healthy" if db_status == "ok" else "degraded",
            "db": db_status,
            "snapshot_count": snapshot_count,
            "last_refresh_at": last_refresh_at,
            "signups": db.count_signups(),
        })

    @app.route("/api/signup", methods=["POST"])
    def signup():
        # Accept both JSON (from JS fetch) and form-encoded (JS-disabled fallback)
        data = request.get_json(silent=True) or request.form.to_dict() or {}
        email = (data.get("email") or "").strip().lower()
        if not email or len(email) > 254 or not EMAIL_RE.match(email):
            wants_json = "application/json" in (request.headers.get("Accept") or "")
            if wants_json:
                return jsonify({"error": "invalid email"}), 400
            return redirect("/?error=invalid", code=303)

        ip = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        ip_hash = _hash_ip(ip.split(",")[0].strip()) if ip else None
        referrer = request.headers.get("Referer")

        signup_id = db.insert_signup(email, ip_hash=ip_hash, referrer=referrer)
        # Email send is best-effort; failures are logged inside the client.
        email_client.send_confirmation(email)

        # JS clients send Accept: application/json. JS-off form posts get redirected
        # to a static thank-you page so the user sees confirmation without JS.
        wants_json = "application/json" in (request.headers.get("Accept") or "")
        if wants_json:
            return jsonify({"signup_id": signup_id})
        return redirect("/thanks.html", code=303)

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

    @app.route("/api/go", methods=["POST"])
    def api_go():
        payload = request.get_json(silent=True) or {}
        origin = payload.get("origin_iata")
        budget = payload.get("budget_usd")
        nights = payload.get("trip_nights")
        vibes = payload.get("vibes") or []

        if not origin or not budget or nights not in VALID_TRIP_NIGHTS:
            return jsonify({"error": "missing or invalid fields"}), 400
        if not isinstance(vibes, list):
            return jsonify({"error": "vibes must be a list"}), 400

        resp = make_response()
        # In tests/dev, requests are HTTP not HTTPS; mark cookie non-secure so it
        # round-trips. Flask's test client treats secure cookies as missing.
        is_dev = app.debug or app.testing or not request.is_secure
        session_id = _get_or_create_session_id(request, resp, is_dev=is_dev)

        if not db_path:
            return jsonify({"error": "database not configured"}), 500
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            candidates = db.find_candidates(conn, origin, int(budget), int(nights))
            seen = db.session_seen_counts(conn, session_id)

            scored = []
            for c in candidates:
                cand = rankmod.Candidate(
                    iata=c["iata"],
                    price_usd=c["price_usd"],
                    vibes=c["vibes"],
                    novelty_score=c["novelty_score"],
                    cheapest_date_in_best_months=c["cheapest_date_in_best_months"],
                )
                query = rankmod.UserQuery(
                    origin_iata=origin, budget_usd=int(budget),
                    trip_nights=int(nights), vibes=vibes,
                )
                session = rankmod.SessionState(seen_count=seen)
                s = rankmod.score(cand, query, session)
                if s is None:
                    continue
                if vibes:
                    overlap = len(set(vibes) & set(c["vibes"]))
                    if overlap == 0:
                        continue
                scored.append((s, c))

            # High score first; tie-break novelty desc then price asc
            scored.sort(key=lambda x: (-x[0], -x[1]["novelty_score"], x[1]["price_usd"]))
            top = scored[:8]

            cards = []
            for _score, c in top:
                cards.append({
                    "iata": c["iata"],
                    "city": c["city"],
                    "country": c["country"],
                    "price_usd": c["price_usd"],
                    "trip_nights": int(nights),
                    "departure_date": c["departure_date"],
                    "return_date": c["return_date"],
                    "catch": catchmod.compose(c["base_catch"], c["route_catch_text"]),
                    "best_months": c["best_months"],
                    "avg_daily_cost_usd": c["avg_daily_cost_usd"],
                    "vibes": c["vibes"],
                    "google_flights_url": _google_flights_url(origin, c["city"]),
                })

            db.record_search(
                conn,
                session_id=session_id,
                origin_iata=origin,
                budget_usd=int(budget),
                trip_nights=int(nights),
                vibe_filter=vibes,
                result_iatas=[card["iata"] for card in cards],
            )
            conn.commit()
        finally:
            conn.close()

        body = {"results": cards}
        resp.data = jsonify(body).get_data()
        resp.content_type = "application/json"
        return resp

    return app


# Flask CLI entry — `flask run` discovers `app` here when FLASK_APP=server.app
app = create_app()
