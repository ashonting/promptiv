#!/usr/bin/env bash
set -euo pipefail

# ─── Colors ──────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
NC='\033[0m'  # No Color

# ─── Paths ───────────────────────────────────────────────────────────────
REPO_ROOT=/srv/prompt-fine-tuner
DASHBOARD_DIR=$REPO_ROOT/frontend/dashboard
WEB_ROOT=/srv/www/promptiv
DASHBOARD_WEB_DIR=$WEB_ROOT/dashboard

# ─── Build Dashboard ─────────────────────────────────────────────────────
echo -e "${GREEN}Step 1: Building React dashboard...${NC}"
pushd "$DASHBOARD_DIR" >/dev/null
npm ci
npm run build
popd >/dev/null

# ─── Deploy to NGINX ──────────────────────────────────────────────────────
echo -e "${GREEN}Step 2: Deploying dashboard to Nginx directory...${NC}"
sudo mkdir -p "$DASHBOARD_WEB_DIR"
sudo rm -rf "$DASHBOARD_WEB_DIR"/*
sudo cp -r "$DASHBOARD_DIR/dist/"* "$DASHBOARD_WEB_DIR/"
sudo chown -R www-data:www-data "$WEB_ROOT"
sudo chmod -R 755 "$WEB_ROOT"

# ─── Reload Nginx ─────────────────────────────────────────────────────────
echo -e "${GREEN}Step 3: Testing & reloading Nginx...${NC}"
sudo nginx -t
sudo systemctl reload nginx

# ─── Cleanup Stray Container ──────────────────────────────────────────────
echo -e "${GREEN}Step 4: Removing stray promptiv-app container if present...${NC}"
if sudo docker ps -a --filter "name=promptiv-app" --format '{{.Names}}' | grep -q .; then
  sudo docker rm -f promptiv-app
fi

# ─── Restart Backend ──────────────────────────────────────────────────────
echo -e "${GREEN}Step 5: Restarting backend via Docker Compose...${NC}"
pushd "$REPO_ROOT" >/dev/null
sudo docker compose down --remove-orphans
sudo docker compose up -d --build --remove-orphans
popd >/dev/null

# ─── Done ─────────────────────────────────────────────────────────────────
echo -e "${GREEN}Step 6: Redeploy complete!${NC}"
echo "You can now test at: https://promptiv.io"
