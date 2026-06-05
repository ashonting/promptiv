# Promptiv

**Live at https://promptiv.io** — a curated "cheap trips, not cheap flights" product for
12 U.S. cities. Total trip cost (airfare + a week on the ground) reveals where your budget
actually reaches; a week in Medellín costs less than a week in Las Vegas.

**Start here:** [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — complete current-state
overview (data model, engine, cron pipeline, page types, SEO system, deploy).

Repo layout:
- `docs/ARCHITECTURE.md` — **the system, as built** (read this first)
- `PRODUCT-BRIEF.md` — product concept / north star
- `docs/plans/2026-06-04-cheap-trips-pivot.md` — the strategic pivot (executed)
- `server/` — Flask API + the generation engine (pairings, hubs, budget, comparisons, digest)
- `public/` — the static site (regenerated daily from the DB)
- `scripts/generate_hubs.py` — the generator (runs nightly on the droplet)
- `tests/` — pytest (120 tests)
- `deploy/` — nginx config, systemd units, `DEPLOY.md`

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
