#!/usr/bin/env bash
# vigilX server setup — fresh Ubuntu 22.04/24.04, run as root:
#   DUCKDNS_TOKEN=xxxx CERT_EMAIL=you@example.com bash setup.sh
#
# Put backend-fixes.patch and firebase_credentials.json next to this script first.
# Safe to re-run: existing secrets are reused from /root/vigilx-secrets.env.
set -euo pipefail

# ── Settings ────────────────────────────────────────────────────────────────
DOMAIN="${DOMAIN:-vigilx.duckdns.org}"
DUCKDNS_SUB="${DOMAIN%%.duckdns.org}"
DUCKDNS_TOKEN="${DUCKDNS_TOKEN:?set DUCKDNS_TOKEN (from duckdns.org)}"
CERT_EMAIL="${CERT_EMAIL:?set CERT_EMAIL for LetsEncrypt notices}"
REPO="${REPO:-https://github.com/Ibrah-N/anti_theft_app.git}"
APP_DIR=/root/anti_theft_app
BACKEND="$APP_DIR/backend"
MEDIA=/var/vigilx-media
MQTT_USER="${MQTT_USER:-smartguard}"
DB_NAME=smartguard
DB_USER=smartguard
HERE="$(cd "$(dirname "$0")" && pwd)"
SECRETS=/root/vigilx-secrets.env

log() { echo -e "\n\033[1;32m==> $*\033[0m"; }
[ "$(id -u)" = 0 ] || { echo "Run as root"; exit 1; }

# ── 1. Packages ─────────────────────────────────────────────────────────────
log "Installing packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q git curl python3-venv python3-pip postgresql nginx certbot \
  mosquitto mosquitto-clients coturn ffmpeg dnsutils

# ── 2. Secrets (generated once, reused on re-run) ───────────────────────────
log "Secrets"
if [ ! -f "$SECRETS" ]; then
  cat > "$SECRETS" <<EOF
DB_PASSWORD=$(openssl rand -hex 24)
SECRET_KEY=$(openssl rand -hex 32)
MQTT_PASSWORD=$(openssl rand -hex 24)
TURN_SECRET=$(openssl rand -hex 32)
EOF
  chmod 600 "$SECRETS"
fi
# shellcheck disable=SC1090
source "$SECRETS"

# ── 3. IPs ──────────────────────────────────────────────────────────────────
PRIVATE_IP=$(ip -4 route get 1.1.1.1 | awk '{for(i=1;i<=NF;i++) if($i=="src") print $(i+1)}')
PUBLIC_IP=$(curl -s --max-time 3 http://100.100.100.200/latest/meta-data/eipv4 || true)
[[ "$PUBLIC_IP" =~ ^[0-9.]+$ ]] || PUBLIC_IP=$(curl -s --max-time 5 https://api.ipify.org)
echo "private=$PRIVATE_IP public=$PUBLIC_IP"

# ── 4. DuckDNS → new IP, plus 5-min cron ────────────────────────────────────
log "DuckDNS"
mkdir -p /root/duckdns
cat > /root/duckdns/duck.sh <<EOF
#!/bin/bash
curl -s "https://www.duckdns.org/update?domains=$DUCKDNS_SUB&token=$DUCKDNS_TOKEN&ip=" -o /root/duckdns/duck.log
EOF
chmod 700 /root/duckdns/duck.sh
/root/duckdns/duck.sh; echo "duckdns: $(cat /root/duckdns/duck.log)"
( crontab -l 2>/dev/null | grep -v duck.sh; echo "*/5 * * * * /root/duckdns/duck.sh >/dev/null 2>&1" ) | crontab -
for i in $(seq 1 30); do
  [ "$(dig +short "$DOMAIN" @1.1.1.1 | tail -1)" = "$PUBLIC_IP" ] && break
  echo "waiting for DNS ($i)..."; sleep 10
done

# ── 5. PostgreSQL ───────────────────────────────────────────────────────────
log "PostgreSQL"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE USER $DB_USER"
sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD'"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" | grep -q 1 \
  || sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER"

# ── 6. TLS certificate (standalone, nginx paused during issue/renew) ────────
log "Let's Encrypt"
if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
  systemctl stop nginx || true
  certbot certonly --standalone -d "$DOMAIN" -m "$CERT_EMAIL" --agree-tos -n \
    --pre-hook "systemctl stop nginx" --post-hook "systemctl start nginx"
fi
# Copy certs where coturn and mosquitto (non-root users) can read them
cat > /etc/letsencrypt/renewal-hooks/deploy/vigilx-certs.sh <<EOF
#!/bin/bash
L=/etc/letsencrypt/live/$DOMAIN
mkdir -p /etc/turnserver/certs /etc/mosquitto/certs
cp \$L/fullchain.pem \$L/privkey.pem /etc/turnserver/certs/
cp \$L/fullchain.pem \$L/privkey.pem \$L/chain.pem /etc/mosquitto/certs/
chown turnserver:turnserver /etc/turnserver/certs/*.pem
chown mosquitto:mosquitto /etc/mosquitto/certs/*.pem
chmod 600 /etc/turnserver/certs/*.pem /etc/mosquitto/certs/*.pem
systemctl restart coturn mosquitto 2>/dev/null || true
EOF
chmod +x /etc/letsencrypt/renewal-hooks/deploy/vigilx-certs.sh
/etc/letsencrypt/renewal-hooks/deploy/vigilx-certs.sh

# ── 7. Mosquitto ────────────────────────────────────────────────────────────
log "Mosquitto"
cat > /etc/mosquitto/conf.d/vigilx.conf <<'EOF'
allow_anonymous false
password_file /etc/mosquitto/passwd

# Backend only — never exposed
listener 1883 127.0.0.1

# Devices / simulator over TLS
listener 8883
cafile   /etc/mosquitto/certs/chain.pem
certfile /etc/mosquitto/certs/fullchain.pem
keyfile  /etc/mosquitto/certs/privkey.pem
EOF
touch /etc/mosquitto/passwd
mosquitto_passwd -b /etc/mosquitto/passwd "$MQTT_USER" "$MQTT_PASSWORD"
chown mosquitto:mosquitto /etc/mosquitto/passwd; chmod 600 /etc/mosquitto/passwd
systemctl enable mosquitto; systemctl restart mosquitto

# ── 8. coturn ───────────────────────────────────────────────────────────────
log "coturn"
if [ "$PRIVATE_IP" = "$PUBLIC_IP" ]; then EXT="external-ip=$PUBLIC_IP"
else EXT="external-ip=$PUBLIC_IP/$PRIVATE_IP"; fi
cat > /etc/turnserver.conf <<EOF
listening-port=3478
tls-listening-port=5349
listening-ip=$PRIVATE_IP
relay-ip=$PRIVATE_IP
$EXT
min-port=49160
max-port=49200
realm=$DOMAIN
server-name=$DOMAIN
use-auth-secret
static-auth-secret=$TURN_SECRET
cert=/etc/turnserver/certs/fullchain.pem
pkey=/etc/turnserver/certs/privkey.pem
no-tlsv1
no-tlsv1_1
denied-peer-ip=10.0.0.0-10.255.255.255
denied-peer-ip=172.16.0.0-172.31.255.255
denied-peer-ip=192.168.0.0-192.168.255.255
denied-peer-ip=127.0.0.0-127.255.255.255
denied-peer-ip=100.100.100.200-100.100.100.200
# Without this, relaying to its own address fails with "403 Forbidden IP"
allowed-peer-ip=$PRIVATE_IP
no-multicast-peers
no-cli
fingerprint
log-file=/var/log/turnserver.log
EOF
chmod 640 /etc/turnserver.conf; chown root:turnserver /etc/turnserver.conf
[ -f /etc/default/coturn ] && sed -i 's/^#\?TURNSERVER_ENABLED=.*/TURNSERVER_ENABLED=1/' /etc/default/coturn
systemctl enable coturn; systemctl restart coturn

# ── 9. Backend code ─────────────────────────────────────────────────────────
log "Backend"
[ -d "$APP_DIR/.git" ] || git clone -q "$REPO" "$APP_DIR"
if [ -f "$HERE/backend-fixes.patch" ]; then
  cd "$APP_DIR"
  if git apply --check "$HERE/backend-fixes.patch" 2>/dev/null; then
    git apply "$HERE/backend-fixes.patch"; echo "patch applied"
  else echo "patch already applied or not needed — skipping"; fi
fi
cd "$BACKEND"
[ -d venv ] || python3 -m venv venv
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q -r requirements.txt

cat > .env <<EOF
DATABASE_URL=postgresql+psycopg2://$DB_USER:$DB_PASSWORD@localhost:5432/$DB_NAME
SECRET_KEY=$SECRET_KEY
APP_NAME=vigilX
DEBUG=False
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_USERNAME=$MQTT_USER
MQTT_PASSWORD=$MQTT_PASSWORD
MQTT_CLIENT_ID=vigilx_backend
TURN_SECRET=$TURN_SECRET
TURN_HOST=$DOMAIN
MEDIA_ROOT=$MEDIA
EOF
chmod 600 .env

if [ -f "$HERE/firebase_credentials.json" ]; then
  cp "$HERE/firebase_credentials.json" "$BACKEND/"; chmod 600 "$BACKEND/firebase_credentials.json"
fi
[ -f "$BACKEND/firebase_credentials.json" ] || { echo "!! Put firebase_credentials.json in $BACKEND and re-run"; exit 1; }

mkdir -p "$MEDIA"; chmod 755 "$MEDIA"
venv/bin/alembic upgrade head

# ── 10. systemd (bound to localhost; nginx is the only way in) ──────────────
cat > /etc/systemd/system/vigilx.service <<EOF
[Unit]
Description=vigilX FastAPI Backend
After=network.target postgresql.service mosquitto.service

[Service]
User=root
WorkingDirectory=$BACKEND
EnvironmentFile=$BACKEND/.env
ExecStart=$BACKEND/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload; systemctl enable vigilx; systemctl restart vigilx

# ── 11. nginx ───────────────────────────────────────────────────────────────
log "nginx"
cat > /etc/nginx/sites-available/vigilx <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    http2 on;
    server_name $DOMAIN;

    ssl_certificate     /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    proxy_set_header Host              \$host;
    proxy_set_header X-Real-IP         \$remote_addr;
    proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;

    # Camera event-clip segments
    location /api/device/ {
        proxy_pass http://127.0.0.1:8000;
        client_max_body_size 32m;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_request_buffering off;
    }

    # App API (recordings up to 200 MB). No trailing slash: routes live under /api.
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        client_max_body_size 210m;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    location = /health { proxy_pass http://127.0.0.1:8000; }
    location /         { proxy_pass http://127.0.0.1:8000; }
}
EOF
nginx -v 2>&1 | grep -qE '1\.(2[5-9]|[3-9][0-9])' || sed -i '/http2 on;/d' /etc/nginx/sites-available/vigilx
ln -sf /etc/nginx/sites-available/vigilx /etc/nginx/sites-enabled/vigilx
rm -f /etc/nginx/sites-enabled/default
nginx -t; systemctl enable nginx; systemctl restart nginx

# ── 12. Checks ──────────────────────────────────────────────────────────────
log "Checks"
sleep 5
for s in postgresql mosquitto coturn vigilx nginx; do printf "%-11s %s\n" "$s" "$(systemctl is-active $s)"; done
echo -n "health: "; curl -s "https://$DOMAIN/health"; echo
echo -n "mqtt tls: "; timeout 5 mosquitto_sub -h "$DOMAIN" -p 8883 --capath /etc/ssl/certs \
  -u "$MQTT_USER" -P "$MQTT_PASSWORD" -t 'sg/#' -C 1 -W 3 >/dev/null 2>&1 \
  && echo ok || echo "connected/timeout (ok if no messages)"
journalctl -u vigilx -n 15 --no-pager | grep -E "Firebase|MQTT|Subscribed|Error" || true

cat <<EOF

Done. Secrets are in $SECRETS (root only). Copy MQTT_PASSWORD and TURN_SECRET
into the simulator/laptop .env and the ESP32 firmware.
Next: register your user + vehicle in the app, then POST /api/device/key for the camera.
EOF
