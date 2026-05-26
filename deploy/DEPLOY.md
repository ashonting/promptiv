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
