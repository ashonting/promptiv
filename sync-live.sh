#!/usr/bin/env bash
set -euo pipefail

# 0) make sure your VITE_ env is in place:
#    a) create /srv/prompt-fine-tuner/frontend/.env.production with your SUPABASE keys
#    b) Vite will pick it up automatically when you run `npm run build` in each folder

# 1) Sync marketing site
cd /srv/prompt-fine-tuner/frontend

# copy HTML
for page in index login signup pricing terms privacy refund-policy; do
  sudo cp -v "${page}.html" "/srv/www/promptiv/${page}.html"
done

# static directory
sudo rm -rf /srv/www/promptiv/static
sudo mkdir -p /srv/www/promptiv/static
# your CSS/JS live at the root of frontend
sudo cp -v style.css script.js logo.svg favicon.ico \
            "/srv/www/promptiv/static/"

# 2) Build & sync the dashboard SPA
cd dashboard
npm ci
npm run build

sudo rm -rf /srv/www/promptiv/dashboard
sudo mkdir -p /srv/www/promptiv/dashboard

# copy the built index.html, vite.svg
sudo cp -v dist/index.html dist/vite.svg \
            /srv/www/promptiv/dashboard/

# copy the hashed JS/CSS into /assets
sudo mkdir -p /srv/www/promptiv/dashboard/assets
sudo cp -v dist/assets/* /srv/www/promptiv/dashboard/assets/

echo "✅ sync-live complete"
