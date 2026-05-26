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
