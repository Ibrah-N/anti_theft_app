# vigilX — Production Server Setup & Operations

> Single source of truth for the vigilX backend server: what runs where, how every piece was set up,
> where every credential lives and how to recreate it, and how to operate / rebuild the box.
>
> **This file contains no real secrets.** Values like `<DB_PASSWORD>` are placeholders. The real values live only on the server in `/root/vigilx-secrets.env` and in your password manager.

Built: 5–6 Nov 2026 · Repo: `Ibrah-N/anti_theft_app` (only `backend/` is deployed) · Last verified: all checks in §13 passed.

---

## Contents

1. [Overview & architecture](#1-overview--architecture)
2. [Server inventory](#2-server-inventory)
3. [Credentials & config files — what, where, how](#3-credentials--config-files)
4. [AWS: instance, disk, Elastic IP, security group](#4-aws-setup)
5. [OS: update, swap, packages](#5-os-setup)
6. [DuckDNS](#6-duckdns)
7. [Secrets file](#7-secrets-file)
8. [PostgreSQL](#8-postgresql)
9. [TLS certificate + renewal hooks](#9-tls-certificate)
10. [Mosquitto (MQTT)](#10-mosquitto)
11. [coturn (TURN)](#11-coturn)
12. [Backend app + systemd](#12-backend)
13. [nginx](#13-nginx)
14. [Verification tests](#14-verification)
15. [Clients: app, simulator, ESP32](#15-clients)
16. [Day-to-day operations](#16-operations)
17. [Backup, restore, migrate to a new server](#17-backup-restore-migrate)
18. [Rotating secrets](#18-rotating-secrets)
19. [Troubleshooting & lessons learned](#19-troubleshooting)

---

## 1. Overview & architecture

```
                         ┌──────────────────────── AWS EC2 (Ubuntu 24.04, ARM) ───────────────────────┐
 Phone app ──HTTPS/WSS :443──►  nginx  ──►  uvicorn/FastAPI 127.0.0.1:8000  ──►  PostgreSQL 127.0.0.1:5432
                               (TLS)          │   │                                   (db: smartguard)
                                              │   └─► /var/vigilx-media  (photos, clips)
                                              │
                                              └──►  Mosquitto 127.0.0.1:1883 (plain, local only)
 ESP32 / simulator ─────MQTT over TLS :8883──►  Mosquitto :8883
 Phone ◄──── WebRTC video (direct, or relayed) ────► camera
             relay: coturn :3478 udp/tcp, :5349 tls, UDP 49160-49200
                         └────────────────────────────────────────────────────────────────────────────┘
 DNS: vigilx.duckdns.org → Elastic IP (DuckDNS, refreshed by cron)
 TLS: Let's Encrypt cert, auto-renewed; copies for coturn + Mosquitto refreshed by a hook
 Push notifications: backend → Firebase (firebase_credentials.json)
```

Rules the design follows:

- Only nginx (443/80), Mosquitto TLS (8883) and coturn are exposed. Postgres, the backend (8000) and plain MQTT (1883) listen on localhost only.
- All secrets are random, generated on the server, and kept in one root-only file.
- Everything survives a reboot and recovers itself (systemd, cron, certbot timer).

---

## 2. Server inventory

| Item | Value |
|---|---|
| Provider | AWS EC2, free plan ($200 credit / 6 months, from 5 Nov 2026) |
| Region / AZ | `ap-southeast-2` (Sydney) / `ap-southeast-2b`. Region selection was locked on this account. Mumbai `ap-south-1` would cut latency from Pakistan by ~200 ms |
| Instance type | `t4g.small`: 2 vCPU (ARM Graviton), 2 GiB RAM |
| AMI | Ubuntu Server 24.04 LTS, 64-bit (Arm) |
| Disk | 30 GiB gp3 (created as 8, grown to 30) + 2 GiB swap file |
| Public IP | Elastic IP `16.178.147.129` |
| Private IP | `172.31.34.29` |
| Domain | `vigilx.duckdns.org` |
| SSH | `ssh -i agies_aws.pem ubuntu@vigilx.duckdns.org`, then `sudo -i` |
| SSH key | ED25519, `agies_aws.pem` (on your Mac only; AWS keeps no copy) |
| Python | 3.12.3 (system), app runs in `backend/venv` |
| nginx | 1.24.0 |

**AWS free plan warning:** when the credits run out or 6 months pass (~May 2027), AWS **closes the account** unless you upgrade to paid. Before then: take a backup (§17), then either upgrade or migrate. Track credits under Billing → Credits.

Previous server (dead): Alibaba ECS, Singapore, public `47.236.73.110`, private `172.18.65.233`.

---

## 3. Credentials & config files

### 3.1 Map of every sensitive file

| File | On | Contains | Created by | Perms | In git? |
|---|---|---|---|---|---|
| `/root/vigilx-secrets.env` | server | the 4 master secrets | `openssl rand` (§7) | `600 root` | **never** |
| `/root/anti_theft_app/backend/.env` | server | all backend settings incl. secrets | `cat > .env` from secrets file (§12) | `600 root` | no (`.gitignore`) |
| `/root/anti_theft_app/backend/firebase_credentials.json` | server | Firebase service-account private key | Firebase console (§3.4) | `600 root` | **never** |
| `/etc/mosquitto/passwd` | server | MQTT user + **hashed** password | `mosquitto_passwd` (§10) | `600 mosquitto` | n/a |
| `/etc/turnserver.conf` | server | coturn config incl. `static-auth-secret` | §11 | `640 root:turnserver` | n/a |
| `/root/duckdns/duck.sh` | server | DuckDNS token | §6 | `700 root` | n/a |
| `/etc/letsencrypt/live/vigilx.duckdns.org/*` | server | TLS cert + private key | certbot (§9) | root only | n/a |
| `/etc/turnserver/certs/*.pem` | server | copy of cert + key for coturn | renewal hook (§9) | `600 turnserver` | n/a |
| `/etc/mosquitto/certs/*.pem` | server | copy of cert + key + chain for Mosquitto | renewal hook (§9) | `600 mosquitto` | n/a |
| `agies_aws.pem` | your Mac | SSH private key | AWS key-pair wizard | `400` | **never** |
| simulator `.env` | your Mac | MQTT + TURN secrets, device key | by hand (§15) | — | no |
| ESP32 firmware config | device | MQTT password | by hand (§15) | — | keep out of git |

Keep a copy of every secret in a password manager. Losing `/root/vigilx-secrets.env` is recoverable: generate new ones and update all users of them (§18). Losing the Firebase key is also recoverable: generate a new one.

### 3.2 `/root/vigilx-secrets.env` — master secrets

```dotenv
DB_PASSWORD=<48 hex chars>
SECRET_KEY=<64 hex chars>
MQTT_PASSWORD=<48 hex chars>
TURN_SECRET=<64 hex chars>
```

| Secret | Generated with | Used by | Must match |
|---|---|---|---|
| `DB_PASSWORD` | `openssl rand -hex 24` | backend → Postgres | Postgres user `smartguard` password, `.env DATABASE_URL` |
| `SECRET_KEY` | `openssl rand -hex 32` | signs JWT access/refresh tokens | `.env` only. Changing it logs every user out |
| `MQTT_PASSWORD` | `openssl rand -hex 24` | backend, simulator, ESP32 | `/etc/mosquitto/passwd`, `.env`, simulator `.env`, firmware |
| `TURN_SECRET` | `openssl rand -hex 32` | backend + simulator generate TURN logins; coturn verifies | `turnserver.conf static-auth-secret`, `.env`, simulator `.env` |

Load into a root shell before any step that uses them:
```bash
sudo -i
source /root/vigilx-secrets.env
echo ${#DB_PASSWORD} ${#SECRET_KEY} ${#MQTT_PASSWORD} ${#TURN_SECRET}   # 48 64 48 64
```

### 3.3 `backend/.env` — backend settings

```dotenv
DATABASE_URL=postgresql+psycopg2://smartguard:<DB_PASSWORD>@localhost:5432/smartguard
SECRET_KEY=<SECRET_KEY>
APP_NAME=vigilX
DEBUG=False
MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_USERNAME=smartguard
MQTT_PASSWORD=<MQTT_PASSWORD>
MQTT_CLIENT_ID=vigilx_backend
TURN_SECRET=<TURN_SECRET>
TURN_HOST=vigilx.duckdns.org
MEDIA_ROOT=/var/vigilx-media
```

Read by `app/core/config.py` (pydantic-settings) and by `alembic/env.py`, which takes `DATABASE_URL` from settings; `alembic.ini` is only a fallback. systemd also loads it via `EnvironmentFile`. The backend reads it **only at startup**, so run `systemctl restart vigilx` after any change.

Settings with defaults in `config.py` that don't need to be set: `ALGORITHM=HS256`, `ACCESS_TOKEN_EXPIRE_MINUTES=30`, `REFRESH_TOKEN_EXPIRE_DAYS=7`, `MEDIA_MIN_FREE_BYTES` (500 MB), `MEDIA_MAX_SNAPSHOT_BYTES` (5 MB), `MEDIA_MAX_RECORDING_BYTES` (200 MB), `CLIP_MAX_SECONDS=300`, `CLIP_MAX_SEGMENTS=40`, `CLIP_MAX_SEGMENT_BYTES` (30 MB), `CLIP_STALE_HOURS=24`.

Required with no default: `DATABASE_URL`, `SECRET_KEY`, `MQTT_HOST`, `MQTT_USERNAME`, `MQTT_PASSWORD`, `TURN_SECRET`. Also note that **`MQTT_PORT` defaults to 8883 in code**, so `1883` must be set here explicitly.

### 3.4 `backend/firebase_credentials.json` — Firebase Admin key

Used by `app/main.py` at startup (`credentials.Certificate("firebase_credentials.json")`, a **relative path**, which is why systemd's `WorkingDirectory` must be `backend/`) to send push notifications.

**How to create:** Firebase Console → project **aegis-vigilx** → ⚙️ Project settings → **Service accounts** → **Generate new private key** → downloads `aegis-vigilx-firebase-adminsdk-…json`. Rename it to `firebase_credentials.json`. Delete old keys in Google Cloud Console → IAM → Service accounts → the `firebase-adminsdk` account → Keys.

**Structure** (values redacted):
```json
{
  "type": "service_account",
  "project_id": "aegis-vigilx",
  "private_key_id": "<40 hex>",
  "private_key": "-----BEGIN PRIVATE KEY-----\n<...>\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-fbsvc@aegis-vigilx.iam.gserviceaccount.com",
  "client_id": "<digits>",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/...",
  "universe_domain": "googleapis.com"
}
```

**Upload** from your Mac, then move it into place on the server:
```bash
scp -i agies_aws.pem firebase_credentials.json ubuntu@vigilx.duckdns.org:/tmp/
# on server, as root:
mv /tmp/firebase_credentials.json /root/anti_theft_app/backend/
chown root:root /root/anti_theft_app/backend/firebase_credentials.json
chmod 600 /root/anti_theft_app/backend/firebase_credentials.json
```

Not to be confused with `google-services.json`, which is the Flutter app's **public** client config and lives in the app, not on the server.

### 3.5 `/etc/mosquitto/passwd` — MQTT users

One line per user: `smartguard:$7$101$<salt>$<hash>`. The password is stored **hashed**, so you can't read it back. The real value is in the secrets file.
```bash
mosquitto_passwd -c -b /etc/mosquitto/passwd smartguard "$MQTT_PASSWORD"   # -c creates/overwrites the file
mosquitto_passwd -b /etc/mosquitto/passwd another_user "<pw>"              # add a user (no -c!)
systemctl restart mosquitto
```

### 3.6 TURN credentials (generated, never stored)

coturn runs in "REST API" mode (`use-auth-secret`). Nobody has a fixed TURN password. Each login is derived from `TURN_SECRET`:
```
username = "<unix expiry timestamp>:<any label>"
password = base64( HMAC-SHA1( TURN_SECRET, username ) )
```
The backend creates these for the app, and the simulator creates its own. To make one by hand for testing:
```bash
U="$(( $(date +%s) + 3600 )):test"
P=$(echo -n "$U" | openssl dgst -binary -sha1 -hmac "$TURN_SECRET" | base64)
echo "$U"; echo "$P"
```

### 3.7 Camera device key

Each vehicle has a device key for the event-clip upload API (`/api/device/clips…`). Only its hash is stored in the DB (`vehicles.device_key_hash`).
- Create or replace: `POST https://vigilx.duckdns.org/api/device/key` while logged in as the vehicle owner (Swagger: `/docs` → Authorize → try it). The response shows the key **once**.
- Put it in the camera firmware and in the simulator `.env` as `DEVICE_KEY`.
- Calling it again replaces the key and immediately disables the old one. Use that if a key leaks.
- A DB restore keeps existing keys. A fresh DB needs a new one.

---

## 4. AWS setup

**Launch instance** (EC2 → Launch instances):
1. AMI: Ubuntu Server 24.04 LTS, Architecture **64-bit (Arm)**. The description is identical for x86, so check the dropdown.
2. Type: `t4g.small`. The free plan only lists free-tier-eligible types, so micro/small.
3. Key pair: new, **ED25519**, **.pem**. Then `chmod 400` it on your Mac.
4. Network settings → **Edit** → create a security group with the rules below. If you skip *Edit*, you get a default `launch-wizard-N` group with SSH only, open to the world.
5. Storage: **30 GiB gp3**. File systems: **None**.

**Security group (inbound):**

| Type | Protocol | Port | Source | Purpose |
|---|---|---|---|---|
| SSH | TCP | 22 | **My IP** | admin |
| HTTP | TCP | 80 | 0.0.0.0/0 | redirect + Let's Encrypt |
| HTTPS | TCP | 443 | 0.0.0.0/0 | API + WebSocket |
| Custom TCP | TCP | 8883 | 0.0.0.0/0 | MQTT over TLS |
| Custom TCP | TCP | 3478 | 0.0.0.0/0 | TURN over TCP |
| Custom UDP | UDP | 3478 | 0.0.0.0/0 | STUN/TURN |
| Custom TCP | TCP | 5349 | 0.0.0.0/0 | TURN over TLS |
| Custom UDP | UDP | 49160-49200 | 0.0.0.0/0 | TURN relay range |

Never open 1883, 8000, 5432 or 3389. AWS writes port ranges with `-`; Alibaba used `/`.

Home IPs in Pakistan change. If SSH times out: Security Groups → your group → Edit inbound rules → SSH → Source *My IP* → Save.

**Elastic IP:** EC2 → Elastic IPs → Allocate → Actions → Associate → the instance. Without it the public IP changes on every stop/start, which breaks coturn's `external-ip`.

**Grow the disk** (created at 8 GiB). Console: instance → Storage → volume → Actions → Modify volume → 30. Then on the server:
```bash
lsblk                                    # console calls it /dev/sda1; Ubuntu sees nvme0n1
growpart /dev/nvme0n1 1                  # stretch partition 1 to fill the disk
resize2fs /dev/nvme0n1p1                 # stretch the ext4 filesystem
df -h /                                  # ~29G
```
EBS volumes can grow, never shrink, and can be modified once per 6 hours.

---

## 5. OS setup

```bash
sudo -i                                   # everything below as root (# prompt)
apt update && apt upgrade -y              # pink "restart services" screen → Enter
timedatectl set-timezone Asia/Karachi

# 2 GB swap — 2 GiB RAM is tight for pip installs and spikes
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

apt install -y git curl dnsutils python3-venv python3-pip \
  postgresql nginx certbot mosquitto mosquitto-clients coturn ffmpeg
```

| Package | Role |
|---|---|
| postgresql | database |
| nginx | HTTPS reverse proxy |
| certbot | Let's Encrypt certificates |
| mosquitto, mosquitto-clients | MQTT broker + `mosquitto_pub`/`mosquitto_sub` test tools |
| coturn | TURN/STUN server |
| ffmpeg | joins event-clip segments (`app/services/clip_storage.py`) |
| python3-venv | isolated Python env for the app |
| dnsutils | `dig` for DNS checks |

Check: `free -h` → Swap 2.0Gi; `systemctl is-active postgresql nginx mosquitto` → all active.

---

## 6. DuckDNS

Account: duckdns.org (Google login with the IMSciences address). Subdomain: `vigilx`. Token: shown on the DuckDNS page.

```bash
TOKEN=<DUCKDNS_TOKEN>
mkdir -p /root/duckdns
cat > /root/duckdns/duck.sh <<EOF
#!/bin/bash
curl -s "https://www.duckdns.org/update?domains=vigilx&token=$TOKEN&ip=" -o /root/duckdns/duck.log
EOF
chmod 700 /root/duckdns/duck.sh
/root/duckdns/duck.sh && cat /root/duckdns/duck.log        # OK
(crontab -l 2>/dev/null; echo "*/5 * * * * /root/duckdns/duck.sh >/dev/null 2>&1") | crontab -
```

`ip=` empty tells DuckDNS to use the IP the request comes from. The cron job re-sends it every 5 minutes, which is a safety net when you have an Elastic IP.

Check: `dig +short vigilx.duckdns.org @1.1.1.1` = Elastic IP.

To rotate the token: DuckDNS page → recreate token → update `duck.sh`.

---

## 7. Secrets file

```bash
cat > /root/vigilx-secrets.env <<EOF
DB_PASSWORD=$(openssl rand -hex 24)
SECRET_KEY=$(openssl rand -hex 32)
MQTT_PASSWORD=$(openssl rand -hex 24)
TURN_SECRET=$(openssl rand -hex 32)
EOF
chmod 600 /root/vigilx-secrets.env
source /root/vigilx-secrets.env
```

The file is kept **outside** the repo on purpose: one `git add .` inside the repo could otherwise publish it. A TURN secret was previously committed to `config.py` that way. Copy all four values to your password manager.

---

## 8. PostgreSQL

```bash
sudo -u postgres psql -c "CREATE USER smartguard WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "CREATE DATABASE smartguard OWNER smartguard;"
```

The names are `smartguard` because that's what the repo uses. Old notes mentioning `vigilx_db` / `vigilx` or `smartguard_user` are wrong. Postgres listens on localhost only by default.

Check: `psql "postgresql://smartguard:$DB_PASSWORD@localhost/smartguard" -c 'select current_user;'`

The tables are created later by Alembic (§12).

---

## 9. TLS certificate

### 9.1 Issue
```bash
systemctl stop nginx                     # certbot --standalone needs port 80
certbot certonly --standalone -d vigilx.duckdns.org -m sanaullahafd07@gmail.com --agree-tos -n
systemctl start nginx
```
Files: `/etc/letsencrypt/live/vigilx.duckdns.org/{fullchain,privkey,chain,cert}.pem`. Key type ECDSA, valid 90 days. `certbot.timer` checks twice a day and renews at about 30 days left.

### 9.2 Renewal hooks

Run once at setup. Certbot then runs them automatically on every renewal.

```bash
# pre: free port 80 for standalone renewal
echo -e '#!/bin/bash\nsystemctl stop nginx'  > /etc/letsencrypt/renewal-hooks/pre/stop-nginx.sh
# post: always start nginx again
echo -e '#!/bin/bash\nsystemctl start nginx' > /etc/letsencrypt/renewal-hooks/post/start-nginx.sh
chmod +x /etc/letsencrypt/renewal-hooks/pre/stop-nginx.sh /etc/letsencrypt/renewal-hooks/post/start-nginx.sh

# deploy: after a successful renewal, give coturn + Mosquitto their own readable copies
cat > /etc/letsencrypt/renewal-hooks/deploy/vigilx-certs.sh <<'EOF'
#!/bin/bash
L=/etc/letsencrypt/live/vigilx.duckdns.org
mkdir -p /etc/turnserver/certs /etc/mosquitto/certs
cp $L/fullchain.pem $L/privkey.pem /etc/turnserver/certs/
cp $L/fullchain.pem $L/privkey.pem $L/chain.pem /etc/mosquitto/certs/
chown turnserver:turnserver /etc/turnserver/certs/*.pem
chown mosquitto:mosquitto /etc/mosquitto/certs/*.pem
chmod 600 /etc/turnserver/certs/*.pem /etc/mosquitto/certs/*.pem
systemctl restart coturn mosquitto 2>/dev/null || true
EOF
chmod +x /etc/letsencrypt/renewal-hooks/deploy/vigilx-certs.sh
/etc/letsencrypt/renewal-hooks/deploy/vigilx-certs.sh       # seed the copies now
```

The copies are needed because coturn and Mosquitto run as non-root users and can't read `/etc/letsencrypt/live/*/privkey.pem`.

Check: `certbot certificates` (about 89 days) and `certbot renew --dry-run` ("all simulated renewals succeeded"). Run the dry run again any time you change the hooks.

---

## 10. Mosquitto

`/etc/mosquitto/conf.d/vigilx.conf`:
```conf
allow_anonymous false
password_file /etc/mosquitto/passwd

# Plain MQTT — only the backend on this machine uses it
listener 1883 127.0.0.1

# Encrypted MQTT — ESP32 and simulator connect here from the internet
listener 8883
cafile   /etc/mosquitto/certs/chain.pem
certfile /etc/mosquitto/certs/fullchain.pem
keyfile  /etc/mosquitto/certs/privkey.pem
```
```bash
mosquitto_passwd -c -b /etc/mosquitto/passwd smartguard "$MQTT_PASSWORD"
chown mosquitto:mosquitto /etc/mosquitto/passwd && chmod 600 /etc/mosquitto/passwd
systemctl enable mosquitto && systemctl restart mosquitto
```

**Topics** (`sg/<device_id>/…`):

| Direction | Topics |
|---|---|
| device → backend | `sensors`, `gps`, `status`, `ack`, `webrtc/offer`, `webrtc/ice`, `camera/state` |
| backend → device | `cmd/lock`, `cmd/start`, `cmd/ac`, `cmd/arm`, `cmd/engine`, `cmd/fuel`, `cmd/gps_request`, `cmd/mirror/{fl,fr,rl,rr}`, `cmd/camera/start`, `cmd/camera/stop`, `cmd/webrtc/answer`, `cmd/webrtc/ice` |

There are no per-topic ACLs; one user `smartguard` is shared by the backend and the devices. If you add ACLs later, devices must still be able to publish to `sg/<id>/camera/state` and the others above.

**Tests:**
```bash
# on the server — two terminals
mosquitto_sub -h vigilx.duckdns.org -p 8883 --capath /etc/ssl/certs -u smartguard -P "$MQTT_PASSWORD" -t test
mosquitto_pub -h 127.0.0.1 -p 1883 -u smartguard -P "$MQTT_PASSWORD" -t test -m hello

# on macOS — note --cafile, not --capath (macOS has no /etc/ssl/certs bundle)
mosquitto_sub -d -h vigilx.duckdns.org -p 8883 --cafile /etc/ssl/cert.pem -u smartguard -P '<MQTT_PASSWORD>' -t 'sg/#' -v
# expect: received CONNACK (0) … received SUBACK
```

---

## 11. coturn

AWS NATs the Elastic IP onto the private NIC, so coturn binds to the private IP and advertises the public one.

```bash
PRIVATE_IP=$(hostname -I | awk '{print $1}')                 # 172.31.34.29
PUBLIC_IP=$(dig +short vigilx.duckdns.org @1.1.1.1)          # 16.178.147.129
mkdir -p /var/log/turnserver && chown turnserver:turnserver /var/log/turnserver
```

`/etc/turnserver.conf` (as deployed; written with the variables above):
```conf
listening-port=3478
tls-listening-port=5349
listening-ip=172.31.34.29
relay-ip=172.31.34.29
external-ip=16.178.147.129/172.31.34.29
min-port=49160
max-port=49200
realm=vigilx.duckdns.org
server-name=vigilx.duckdns.org
use-auth-secret
static-auth-secret=<TURN_SECRET>
cert=/etc/turnserver/certs/fullchain.pem
pkey=/etc/turnserver/certs/privkey.pem
no-tlsv1
no-tlsv1_1
denied-peer-ip=10.0.0.0-10.255.255.255
denied-peer-ip=172.16.0.0-172.31.255.255
denied-peer-ip=192.168.0.0-192.168.255.255
denied-peer-ip=127.0.0.0-127.255.255.255
denied-peer-ip=169.254.0.0-169.254.255.255
allowed-peer-ip=172.31.34.29
no-multicast-peers
no-cli
fingerprint
log-file=/var/log/turnserver/turnserver.log
simple-log
```
```bash
chown root:turnserver /etc/turnserver.conf && chmod 640 /etc/turnserver.conf
systemctl enable coturn && systemctl restart coturn
```

| Line | Why |
|---|---|
| `external-ip=PUBLIC/PRIVATE` | without it: `508 Cannot create socket`, no relay candidates |
| `use-auth-secret` + `static-auth-secret` | time-limited HMAC logins (§3.6); must equal `.env TURN_SECRET` |
| `denied-peer-ip …` | stop the relay being used to reach private networks; `169.254/16` = AWS metadata service |
| `allowed-peer-ip=PRIVATE` | without it: `403 Forbidden IP` when relaying to itself (the old Alibaba bug) |
| `log-file` in `/var/log/turnserver/` + `simple-log` | coturn runs as `turnserver` and can't create files directly in `/var/log`; `simple-log` keeps a fixed filename |

**If the instance or Elastic IP changes**, update `listening-ip`, `relay-ip`, `external-ip` and `allowed-peer-ip`, then restart coturn.

Check: `ss -lnup | grep 3478`, `ss -lntp | grep -E '3478|5349'`, `tail /var/log/turnserver/turnserver.log`. End-to-end test in §14.

---

## 12. Backend

### 12.1 Code, dependencies, config
```bash
cd /root
git clone https://github.com/Ibrah-N/anti_theft_app.git
cd anti_theft_app/backend
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt          # 3–5 min on ARM
# firebase_credentials.json → see §3.4
mkdir -p /var/vigilx-media
# .env → see §3.3 (write it with: cat > .env <<EOF … EOF, after `source /root/vigilx-secrets.env`)
chmod 600 .env
grep -c '=$' .env                                  # must be 0 (no empty values)
venv/bin/alembic upgrade head
```

Migrations, in order: `6992040811b1` initial (users, vehicles, alerts) → `f01b9fdc8683` gps_readings → `ca9df87f2abf` device_tokens → `28003cc59777` vehicle control columns → `15b8fd0263a8` camera_media → `787d2c8b5326` sequence_number → `a3c91e7d5b42` device key + event clips + `clip_uploads`.

Tables: `users, vehicles, alerts, gps_readings, device_tokens, camera_media, clip_uploads, alembic_version`.

Repo fixes required before this would run (commit `67b9ba8`, already pushed):
- `requirements.txt`: `httpx==0.28.1`, because `firebase-admin 7.5.0` requires it and `0.27.2` made pip fail.
- `mqtt_service.py`: restored `publish_start_command` (engine start), which had been overwritten by a mis-indented paste; merged the duplicate `publish_camera_start_command`.
- `mqtt_handlers.py`: indentation of `elif msg_type == "webrtc_ice"`.
- `routes/device.py`: removed a double comma (`Depends(get_device_vehicle),,`).
- `alembic/env.py`: reads `DATABASE_URL` from `.env` so the DB password isn't in `alembic.ini`.

Manual test run: `venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000`. Expect `Firebase Admin initialized`, `MQTT connected to broker`, and `Subscribed to sg/+/sensors, … sg/+/camera/state`. Stop with Ctrl+C.

### 12.2 systemd — `/etc/systemd/system/vigilx.service`
```ini
[Unit]
Description=vigilX FastAPI Backend
After=network.target postgresql.service mosquitto.service

[Service]
User=root
WorkingDirectory=/root/anti_theft_app/backend
EnvironmentFile=/root/anti_theft_app/backend/.env
ExecStart=/root/anti_theft_app/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload && systemctl enable --now vigilx
curl -s localhost:8000/health     # {"status":"online","app":"vigilX","mqtt_connected":true}
```
- `WorkingDirectory` must be `backend/`, because the Firebase key is loaded by relative path.
- `127.0.0.1` keeps port 8000 private (the old box used `0.0.0.0` with 8000 open to the internet).
- Background threads started by the app: MQTT client, and media cleanup (30-day retention, runs every 6 h).

---

## 13. nginx

`/etc/nginx/sites-available/vigilx` (symlinked into `sites-enabled`; `default` removed):
```nginx
server {
    listen 80;
    server_name vigilx.duckdns.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name vigilx.duckdns.org;

    ssl_certificate     /etc/letsencrypt/live/vigilx.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/vigilx.duckdns.org/privkey.pem;

    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    location /api/device/ {                 # camera event-clip segments
        proxy_pass http://127.0.0.1:8000;
        client_max_body_size 32m;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
        proxy_request_buffering off;
    }

    location /api/ {                        # app API, recordings up to 200 MB
        proxy_pass http://127.0.0.1:8000;
        client_max_body_size 210m;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    location /ws {                          # live WebSocket
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    location / {                            # /health, /docs, everything else
        proxy_pass http://127.0.0.1:8000;
    }
}
```
```bash
ln -sf /etc/nginx/sites-available/vigilx /etc/nginx/sites-enabled/vigilx
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
# optional: hide version number
sed -i 's/# server_tokens off;/server_tokens off;/' /etc/nginx/nginx.conf && nginx -t && systemctl reload nginx
```

**`proxy_pass` must have no trailing slash.** `http://127.0.0.1:8000/;` strips `/api` from requests, and every route (`/api/auth`, `/api/vehicle`, `/api/alerts`, `/api/gps`, `/api/device`) would return 404.

---

## 14. Verification

All passed on 5–6 Nov 2026.

| # | Test | Command / action | Expected |
|---|---|---|---|
| 1 | HTTPS + backend | `curl https://vigilx.duckdns.org/health` | `"mqtt_connected":true` |
| 2 | HTTP redirect | `curl -I http://vigilx.duckdns.org` | `301`, `Location: https://…` |
| 3 | API docs | browser → `https://vigilx.duckdns.org/docs` | Swagger page, padlock |
| 4 | TURN relay | Trickle ICE page (below) | a `relay` candidate at `16.178.147.129`, port 49160–49200 |
| 5 | MQTT TLS from outside | `mosquitto_sub -d … --cafile /etc/ssl/cert.pem` (Mac) | `CONNACK (0)`, `SUBACK` |
| 6 | App | register, add vehicle `esp-001` | dashboard loads, no reconnect loop |
| 7 | Simulator | run with new `.env` | data in the app, in `mosquitto_sub`, and in `journalctl -u vigilx` |
| 8 | Live video | start a stream from the app | video plays |
| 9 | Reboot | `reboot`, wait 1 min, repeat #1 | still online |

**TURN test:** generate a login (§3.6) → open https://webrtc.github.io/samples/src/content/peerconnection/trickle-ice/ → remove the default server → add `turn:vigilx.duckdns.org:3478` with that username and password → *Gather candidates*. `701 … host lookup` errors are harmless: the IPv6 lookup fails because the domain has no IPv6 address.

---

## 15. Clients

**Flutter app**: `lib/core/constants/app_constants.dart`:
```dart
static const String baseUrl = 'https://vigilx.duckdns.org';
static const String apiUrl  = '$baseUrl/api';
static const String wsUrl   = 'wss://vigilx.duckdns.org/ws';
```
No rebuild is needed while the domain stays the same. If the domain changes, edit these and rebuild the APK. A new `SECRET_KEY` or a fresh DB means users log in or register again.

**Simulator** (`backend/simulator.py`, run on your laptop): its `.env`:
```dotenv
MQTT_HOST=vigilx.duckdns.org
MQTT_PORT=8883
MQTT_USERNAME=smartguard
MQTT_PASSWORD=<MQTT_PASSWORD>
TURN_HOST=vigilx.duckdns.org
TURN_SECRET=<TURN_SECRET>
# event-clip upload testing (optional)
BACKEND_URL=https://vigilx.duckdns.org
DEVICE_KEY=<from POST /api/device/key>
# optional: CAMERA_SOURCE=webcam, CAMERA_INDEX=0, EVENT_AUTO_TRIGGER=false
```
- `DEVICE_ID` is hard-coded as **`esp-001`** (`simulator.py`, line 70). The vehicle in the app must use exactly that ID, or the backend logs `Unknown device_id` and drops every message.
- Uses system CA certs for TLS. If you see `CERTIFICATE_VERIFY_FAILED` on macOS: `pip install certifi && export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")`.
- Extra packages: `pip install -r simulator_requirements.txt` (aiortc, pillow, numpy, opencv-python).

**ESP32 firmware**: host `vigilx.duckdns.org`, port `8883`, user `smartguard`, password `<MQTT_PASSWORD>`. Its TLS root of trust must be **ISRG Root X1** (Let's Encrypt). Device ID must match the vehicle. The camera needs `DEVICE_KEY` for clip uploads.

---

## 16. Operations

| Task | Command (root) |
|---|---|
| Status of everything | `systemctl status vigilx nginx mosquitto coturn postgresql --no-pager` |
| Backend logs (live) | `journalctl -u vigilx -f` |
| Backend logs (last hour) | `journalctl -u vigilx --since "1 hour ago" --no-pager` |
| Restart backend | `systemctl restart vigilx` |
| TURN log | `tail -f /var/log/turnserver/turnserver.log` |
| Mosquitto log | `journalctl -u mosquitto -n 50 --no-pager` |
| nginx errors | `tail -f /var/log/nginx/error.log` |
| Disk / memory | `df -h /` · `free -h` · `du -sh /var/vigilx-media` |
| Cert status | `certbot certificates` · `certbot renew --dry-run` |
| DuckDNS status | `cat /root/duckdns/duck.log` (OK) · `dig +short vigilx.duckdns.org @1.1.1.1` |

**Deploy new code:**
```bash
cd /root/anti_theft_app && git pull
cd backend
venv/bin/pip install -r requirements.txt
venv/bin/alembic upgrade head
systemctl restart vigilx && journalctl -u vigilx -n 30 --no-pager
```

**Get your own login token for Swagger/curl:** `/docs` → `POST /api/auth/login` → copy the access token → **Authorize**.

---

## 17. Backup, restore, migrate

**Backup**: run regularly, and **always** before the AWS credits end:
```bash
mkdir -p /root/backups && cd /root/backups
sudo -u postgres pg_dump -Fc smartguard > smartguard-$(date +%F).dump
tar czf media-$(date +%F).tgz /var/vigilx-media
tar czf config-$(date +%F).tgz /root/vigilx-secrets.env /root/anti_theft_app/backend/.env \
  /root/anti_theft_app/backend/firebase_credentials.json /etc/turnserver.conf \
  /etc/mosquitto/conf.d/vigilx.conf /etc/nginx/sites-available/vigilx \
  /etc/systemd/system/vigilx.service /root/duckdns/duck.sh
```
Copy to your Mac (`config-*.tgz` contains every secret, so keep it private):
```bash
# on server, as root: hand the files to the ubuntu user for download
mkdir -p /home/ubuntu/dl && cp /root/backups/*$(date +%F)* /home/ubuntu/dl/ && chown -R ubuntu /home/ubuntu/dl
# on Mac
scp -i agies_aws.pem 'ubuntu@vigilx.duckdns.org:dl/*' ~/vigilx-backups/
# on server, afterwards
rm -rf /home/ubuntu/dl
```

**Restore onto a set-up server:**
```bash
systemctl stop vigilx
sudo -u postgres dropdb smartguard
sudo -u postgres createdb -O smartguard smartguard
sudo -u postgres pg_restore -d smartguard --no-owner --role=smartguard smartguard-YYYY-MM-DD.dump
cd /root/anti_theft_app/backend && venv/bin/alembic upgrade head
tar xzf media-YYYY-MM-DD.tgz -C /
systemctl start vigilx
```
This keeps users, vehicles and device keys, so clients need no changes as long as the secrets are the same.

**Migrate to a new server / provider** (≈1 hour):
1. Back up (above) and copy it off the server.
2. New VM (Ubuntu 24.04, ≥2 GB RAM), open the ports from §4, get a static public IP.
3. Follow §5 → §13. Reuse the secrets from `config-*.tgz` instead of generating new ones (§7), and clients need no changes.
4. Update the IP-specific coturn lines (§11). If the provider puts the public IP directly on the NIC, drop `external-ip` and use the public IP everywhere.
5. Restore DB + media. Run §14.

---

## 18. Rotating secrets

| Secret | Update in | Then |
|---|---|---|
| `DB_PASSWORD` | `sudo -u postgres psql -c "ALTER USER smartguard WITH PASSWORD '<new>';"` + `.env` | restart vigilx |
| `SECRET_KEY` | `.env` | restart vigilx (everyone logged out) |
| `MQTT_PASSWORD` | `mosquitto_passwd -b /etc/mosquitto/passwd smartguard '<new>'` + `.env` + simulator + firmware | restart mosquitto, vigilx |
| `TURN_SECRET` | `turnserver.conf static-auth-secret` + `.env` + simulator `.env` | restart coturn, vigilx |
| Firebase key | generate new in console, replace file, delete old key | restart vigilx |
| Device key | `POST /api/device/key` | update firmware/simulator |
| DuckDNS token | DuckDNS page → recreate | update `duck.sh` |
| SSH key | new key pair; add its public key to `~ubuntu/.ssh/authorized_keys`; remove the old line | — |

Always update `/root/vigilx-secrets.env` and your password manager too. Generate new values with `openssl rand -hex 32`.

---

## 19. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `apt … Permission denied` | not root. Run `sudo -i` (prompt must end in `#`) |
| `ssh … Permission denied (publickey)` | wrong key file name (needs `.pem`) or wrong key. User is `ubuntu`, not `root` |
| SSH times out | your home IP changed. Security group → SSH → *My IP* |
| `certbot … invalid email` | the placeholder `YOUR_EMAIL` was left in |
| certbot timeout | port 80 closed, or DuckDNS not pointing at this server |
| renewal fails "port 80 in use" | the pre/post nginx hooks are missing (§9.2) |
| `vigilx` restarting in a loop | `journalctl -u vigilx -n 50`: missing `.env` value, missing `firebase_credentials.json`, or a syntax error in pulled code |
| `mqtt_connected:false` | `.env MQTT_PASSWORD` ≠ broker password, or `MQTT_PORT` not set to 1883 |
| `alembic … password authentication failed` | wrong `DATABASE_URL` in `.env`, or secrets not loaded when `.env` was written (`grep -c '=$' .env` must be 0) |
| `pip … ResolutionImpossible` (httpx) | `httpx` must be `0.28.1` for `firebase-admin 7.5.0` |
| `mosquitto_sub … Protocol error` on Mac | use `--cafile /etc/ssl/cert.pem`, not `--capath /etc/ssl/certs` |
| `mosquitto_sub -d vigilx…` "Unknown option" | `-d` is debug, not host. Use `-d -h vigilx.duckdns.org` |
| Simulator data ignored | vehicle `device_id` ≠ `esp-001` ("Unknown device_id" in the logs) |
| Video fails on mobile data | TURN log: `403 Forbidden IP` → `allowed-peer-ip`; `508` → `external-ip`; no relay → UDP 49160–49200 closed or `TURN_SECRET` mismatch |
| TURN log file missing | coturn can't write `/var/log`. Use `/var/log/turnserver/` + `simple-log` |
| Clip upload `413` | `client_max_body_size` in the `/api/device/` block |
| All `/api/*` routes 404 | trailing slash in `proxy_pass` |
| Disk full | `du -sh /var/vigilx-media`; media older than 30 days is auto-deleted; grow the EBS volume (§4) |

**Lessons from this rebuild**
- Write the doc while building, not after. The old server had no docs, and its notes had wrong DB names and a broken nginx line.
- Copy secrets and un-versioned files (`.env`, Firebase key, media, DB dump) off a server **before** a trial or credit period ends.
- Never paste real secrets into chats or screenshots, and never commit them. Rotate anything that was exposed.
- Test a fresh `pip install` + app import before deploying a commit; `main` had shipped with syntax errors.
