#!/usr/bin/env bash
# deploy.sh — One-shot EC2 deployment script
# Run as: bash deploy.sh
# Tested on: Amazon Linux 2023 / Ubuntu 22.04

set -euo pipefail

APP_DIR="/root/myflixdb"
VENV="$APP_DIR/venv"
SERVICE="myflixdb"
LOG_DIR="/var/log/myflixdb"

echo "════════════════════════════════════════════"
echo "  MyFlixDB — EC2 Deployment"
echo "════════════════════════════════════════════"

# ── 1. System packages ───────────────────────────────────────────────
echo "[1/7] Installing system packages …"
sudo yum update -y 2>/dev/null || sudo apt-get update -y
sudo yum install -y python3 python3-pip python3-venv nginx 2>/dev/null \
  || sudo apt-get install -y python3 python3-pip python3-venv nginx

# ── 2. Log directory ─────────────────────────────────────────────────
echo "[2/7] Creating log directory …"
sudo mkdir -p "$LOG_DIR"
sudo chown ec2-user:ec2-user "$LOG_DIR"

# ── 3. Python virtual environment ────────────────────────────────────
echo "[3/7] Setting up Python venv …"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip
"$VENV/bin/pip" install -r "$APP_DIR/requirements.txt"

# ── 4. Environment file ──────────────────────────────────────────────
echo "[4/7] Checking .env …"
if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "⚠️  Created .env from template — fill in your values!"
fi

# ── 5. Systemd service ───────────────────────────────────────────────
echo "[5/7] Registering systemd service …"
sudo cp "$APP_DIR/scripts/myflixdb.service" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE"
sudo systemctl restart "$SERVICE"

# ── 6. nginx config ──────────────────────────────────────────────────
echo "[6/7] Configuring nginx …"
sudo cp "$APP_DIR/scripts/nginx.conf" /etc/nginx/sites-available/myflixdb
sudo ln -sf /etc/nginx/sites-available/myflixdb /etc/nginx/sites-enabled/myflixdb
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx

# ── 7. Verify ────────────────────────────────────────────────────────
echo "[7/7] Verifying …"
sleep 2
STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health || echo "000")
if [ "$STATUS" = "200" ]; then
    echo "✅ Deployment successful! API is live on port 80"
    echo "   Swagger UI: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)/docs"
else
    echo "⚠️  Health check returned HTTP $STATUS — check logs:"
    echo "   sudo journalctl -u myflixdb -n 50"
    echo "   sudo tail -f /var/log/myflixdb/error.log"
fi
