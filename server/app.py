"""Promptiv teaser Flask app."""
import hashlib
import os
import re
from pathlib import Path
from typing import Optional

from flask import Flask, jsonify, request, send_from_directory

from server import db, email_client
from server.migrations import init_schema


# Pragmatic email regex — not RFC-strict but rejects obvious junk.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _hash_ip(ip: Optional[str]) -> Optional[str]:
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


# Flask CLI entry — `flask run` discovers `app` here when FLASK_APP=server.app
app = create_app()
