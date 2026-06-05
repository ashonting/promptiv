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

Run from your laptop (`~/promptiv/`):

```bash
rsync -avz --delete \
    --exclude='.venv' --exclude='.git' --exclude='*.sqlite' \
    --exclude='__pycache__' --exclude='.env' --exclude='.superpowers' \
    --exclude='node_modules' \
    ~/promptiv/ root@promptiv.io:/srv/promptiv/
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

### 11b. Self-host GSAP for production

Before going live, replace the jsDelivr CDN script with a self-hosted copy to remove the third-party dependency.

```bash
# On server:
cd /srv/promptiv/public
mkdir -p vendor
curl -sL https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js -o vendor/gsap-3.12.5.min.js
# Verify size — should be ~70KB
ls -la vendor/gsap-3.12.5.min.js

# Update the script tag in index.html:
sed -i 's|<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js" integrity="[^"]*" crossorigin="anonymous"></script>|<script src="/vendor/gsap-3.12.5.min.js"></script>|' /srv/promptiv/public/index.html

# Verify the change:
grep gsap /srv/promptiv/public/index.html
```

After this, the page has no third-party network dependencies at runtime.

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
cd ~/promptiv
rsync -avz \
    --exclude='.venv' --exclude='.git' --exclude='*.sqlite' \
    --exclude='__pycache__' --exclude='.env' --exclude='.superpowers' \
    --exclude='node_modules' \
    ~/promptiv/ root@promptiv.io:/srv/promptiv/

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

---

# v1 (Trip Discovery Tool) — Shipped 2026-05-26

## What v1 adds

- `/go` page with airport/budget/length/vibe form, server-side ranking, ranked trip cards
- `/api/go` endpoint returning ranked candidates with catch text + Google Flights deep links
- 5 new SQLite tables: airports, destinations, routes, price_snapshots, searches
- YAML curation in `data/` (airports.yaml = 12 hubs, destinations.yaml = 100 dests, routes.yaml = `[]`)
- Nightly `fli` price refresh via systemd timer
- Email gate at 5 searches/session, HTML-styled welcome email via Resend
- New nginx location for `/go` (the SPA fallback was swallowing it)

## Incremental v1 deploy

```bash
# 1. From local: ship code + data + deploy configs (NOT tests/, docs/, spikes)
# NOTE: scripts/generate_hubs.py DOES deploy — the droplet's promptiv-regen.timer
# runs it nightly. Only the spike_* throwaways are excluded.
cd ~/promptiv && rsync -avz --delete \
  --exclude '.git/' --exclude '.venv/' --exclude '.env' \
  --exclude '__pycache__/' --exclude '.pytest_cache/' \
  --exclude 'tests/' --exclude 'docs/' --exclude '.superpowers/' \
  --exclude 'PRODUCT-BRIEF.md' \
  --exclude '*.egg-info/' --exclude '.gitignore' \
  --exclude 'public/vendor/' --exclude 'teaser.dev.sqlite' \
  --exclude 'scripts/spike_*' \
  ./ root@promptiv.io:/srv/promptiv/

# 2. If pyproject.toml changed, install new deps
ssh root@promptiv.io '/srv/promptiv/.venv/bin/pip install -e /srv/promptiv'

# 3. If schema migrations added, run them
ssh root@promptiv.io 'cd /srv/promptiv && DATABASE_PATH=/var/lib/promptiv/teaser.sqlite \
  /srv/promptiv/.venv/bin/python -c "from server.migrations import init_schema; init_schema(\"/var/lib/promptiv/teaser.sqlite\")"'

# 4. If destinations.yaml or airports.yaml or routes.yaml changed, reload curation
ssh root@promptiv.io 'cd /srv/promptiv && DATABASE_PATH=/var/lib/promptiv/teaser.sqlite \
  /srv/promptiv/.venv/bin/python -m server.destinations'

# 5. ALWAYS re-swap GSAP CDN to vendor (rsync clobbers index.html)
ssh root@promptiv.io 'python3 -c "
import re
p = \"/srv/promptiv/public/index.html\"
src = open(p).read()
new = re.sub(r\"<script src=\\\"https://cdn\\.jsdelivr\\.net/.*gsap.*?\\\"[^>]*></script>\",
             \"<script src=\\\"/vendor/gsap-3.12.5.min.js\\\"></script>\", src)
if new != src:
    open(p, \"w\").write(new); print(\"GSAP swapped\")
else: print(\"GSAP unchanged\")
"'

# 6. If nginx config changed, copy + reload
ssh root@promptiv.io 'nginx -t && systemctl reload nginx'

# 7. If Python code changed, restart Flask
ssh root@promptiv.io 'systemctl restart promptiv.service && sleep 2 && systemctl is-active promptiv.service'

# 8. If you need to trigger an immediate price refresh (otherwise the timer fires at 07:00 UTC)
ssh root@promptiv.io 'systemctl start promptiv-refresh.service'

# 9. Verify
curl -s https://promptiv.io/api/healthz | python3 -m json.tool
curl -s -X POST https://promptiv.io/api/go -H 'Content-Type: application/json' \
  -d '{"origin_iata":"BNA","budget_usd":1500,"trip_nights":7,"vibes":[]}' | python3 -m json.tool | head -30
```

## Critical gotchas

- **nginx SPA fallback eats new pages.** The default `try_files $uri $uri/ /index.html` catches any URL Flask should handle. If you add a new page (`/about`, `/help`), add an explicit `location = /<path> { try_files /<path>.html =404; }` block. Bug we hit on v1 launch.
- **GSAP CDN must be re-swapped after every rsync** of `public/index.html`. The repo keeps the CDN tag so local dev works without `public/vendor/`. Step 5 above handles this — don't skip.
- **fli is rate-limited** (HTTP 429 from Google). The cron logs failures and continues. Acceptable up to ~5% failure rate. If higher, run `uv tool upgrade flights` locally and redeploy — the reverse-engineering may need updating.
- **Refresh iterates by destination, not origin.** Don't "fix" this — it spreads load across all 12 origins so /go has coverage within ~3 minutes of refresh start instead of waiting ~30 min for the first origin to finish.

## Monitoring v1

```bash
# Snapshot count growing?
ssh root@promptiv.io '/srv/promptiv/.venv/bin/python -c "
import sqlite3
c = sqlite3.connect(\"/var/lib/promptiv/teaser.sqlite\")
print(\"snapshots:\", c.execute(\"SELECT COUNT(*) FROM price_snapshots\").fetchone()[0])
for r in c.execute(\"SELECT origin_iata, COUNT(*) FROM price_snapshots GROUP BY origin_iata ORDER BY 1\"):
    print(f\"  {r[0]}: {r[1]}\")
"'

# Last refresh run
ssh root@promptiv.io 'tail -50 /var/log/promptiv/price-refresh.log'

# Recent /go searches (analytics)
ssh root@promptiv.io '/srv/promptiv/.venv/bin/python -c "
import sqlite3, json
c = sqlite3.connect(\"/var/lib/promptiv/teaser.sqlite\")
for r in c.execute(\"SELECT origin_iata, budget_usd, trip_nights, vibe_filter, created_at FROM searches ORDER BY id DESC LIMIT 20\"):
    print(f\"{r[4][:19]} | {r[0]} | \${r[1]} | {r[2]}n | vibes={r[3]}\")
"'
```

## Email gate operator workaround

The /go email gate triggers at 5 searches per session. To keep testing past the gate:

- Open devtools console: `localStorage.clear()` and refresh
- Or use an Incognito/Private window (fresh localStorage per session)
