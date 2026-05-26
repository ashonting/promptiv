"""Load YAML curation files into SQLite. Idempotent; safe to re-run."""
import json
import sqlite3
from pathlib import Path

import yaml


def load_all(db_path: str, data_dir: Path) -> None:
    """Upsert airports, destinations, routes from YAML files in data_dir."""
    data_dir = Path(data_dir)
    airports = yaml.safe_load((data_dir / "airports.yaml").read_text())
    destinations = yaml.safe_load((data_dir / "destinations.yaml").read_text())
    routes = yaml.safe_load((data_dir / "routes.yaml").read_text()) or []

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        _upsert_airports(conn, airports)
        _upsert_destinations(conn, destinations)
        _upsert_explicit_routes(conn, routes)
        populate_missing_routes(conn)
        conn.commit()
    finally:
        conn.close()


def _upsert_airports(conn: sqlite3.Connection, airports: list[dict]) -> None:
    for a in airports:
        conn.execute(
            """INSERT INTO airports (iata, city, state, region_us, lat, lng, rank_us)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(iata) DO UPDATE SET
                   city=excluded.city, state=excluded.state, region_us=excluded.region_us,
                   lat=excluded.lat, lng=excluded.lng, rank_us=excluded.rank_us""",
            (a["iata"], a["city"], a.get("state"), a["region_us"],
             a["lat"], a["lng"], a["rank_us"]),
        )


def _upsert_destinations(conn: sqlite3.Connection, destinations: list[dict]) -> None:
    for d in destinations:
        conn.execute(
            """INSERT INTO destinations (
                   iata, city, country, country_code, region, vibes,
                   passport_required, visa_required_us, best_months,
                   avg_daily_cost_usd, safety_tier, currency, lat, lng,
                   base_catch, novelty_score
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(iata) DO UPDATE SET
                   city=excluded.city, country=excluded.country,
                   country_code=excluded.country_code, region=excluded.region,
                   vibes=excluded.vibes, passport_required=excluded.passport_required,
                   visa_required_us=excluded.visa_required_us,
                   best_months=excluded.best_months,
                   avg_daily_cost_usd=excluded.avg_daily_cost_usd,
                   safety_tier=excluded.safety_tier, currency=excluded.currency,
                   lat=excluded.lat, lng=excluded.lng,
                   base_catch=excluded.base_catch, novelty_score=excluded.novelty_score""",
            (
                d["iata"], d["city"], d["country"], d["country_code"], d["region"],
                json.dumps(d["vibes"]),
                1 if d["passport_required"] else 0,
                1 if d["visa_required_us"] else 0,
                json.dumps(d["best_months"]),
                int(d["avg_daily_cost_usd"]),
                int(d["safety_tier"]),
                d["currency"],
                float(d["lat"]), float(d["lng"]),
                d.get("base_catch"),
                int(d["novelty_score"]),
            ),
        )


def _upsert_explicit_routes(conn: sqlite3.Connection, routes: list[dict]) -> None:
    for r in routes:
        conn.execute(
            """INSERT INTO routes (origin_iata, dest_iata, route_catch_text)
               VALUES (?, ?, ?)
               ON CONFLICT(origin_iata, dest_iata) DO UPDATE SET
                   route_catch_text=excluded.route_catch_text""",
            (r["origin"], r["dest"], r.get("catch")),
        )


def populate_missing_routes(conn: sqlite3.Connection) -> None:
    """For every (airport, destination) pair without a routes row, insert with null catch."""
    conn.execute(
        """INSERT OR IGNORE INTO routes (origin_iata, dest_iata, route_catch_text)
           SELECT a.iata, d.iata, NULL
             FROM airports a CROSS JOIN destinations d"""
    )


def main() -> None:
    """CLI entry: `python -m server.destinations` loads from ./data."""
    import os
    db_path = os.environ.get("DATABASE_PATH", "teaser.dev.sqlite")
    data_dir = Path(os.environ.get("DATA_DIR", "data"))
    load_all(db_path, data_dir)
    print(f"Loaded YAML from {data_dir} into {db_path}")


if __name__ == "__main__":
    main()
