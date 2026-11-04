# vigilX server — rebuild guide

Backend: `Ibrah-N/anti_theft_app` → `backend/` (FastAPI + PostgreSQL + Mosquitto + coturn + nginx).
Domain: `vigilx.duckdns.org`. Old box: Alibaba ECS ap-southeast-1, 47.236.73.110 / 172.18.65.233.

Files in this folder:

| File | What it is |
|---|---|
| `setup.sh` | One-shot install of everything below on a fresh Ubuntu box |
| `backend-fixes.patch` | Fixes for the current `main` — **it does not start without them** |
| `SERVER-SETUP.md` | This guide |

---

## 0. Before anything: try to rescue old data

Users, vehicles, device keys, alerts and the gallery live **only** on the old disk. In the ECS console check whether the instance (or its system disk) still exists — expired instances are usually *stopped* for a while before being *released*.

If it still exists: renew it for a day (or create a snapshot → new disk from snapshot), then copy off:

```bash
sudo -u postgres pg_dump smartguard > smartguard.sql
tar czf media.tgz /var/vigilx-media
```

If it is released, start fresh — the app just needs a new account, vehicle and device key (step 5).

## 1. Fix the repo first (current `main` is broken)

I tested the latest commit (`736824b`) in a clean Python venv against a fresh PostgreSQL. Problems found:

1. **`pip install -r requirements.txt` fails** — `firebase-admin==7.5.0` requires `httpx==0.28.1`, file pins `0.27.2`.
2. **Backend can't import** — three copy-paste errors in the last commit:
   - `mqtt_service.py`: the new camera-start method was pasted over **`publish_start_command` (engine start)** with wrong indentation. Engine start was deleted; the method's new `finalize_recording` flag never took effect because an older duplicate below it overrode it.
   - `mqtt_handlers.py`: `elif msg_type == "webrtc_ice"` over-indented.
   - `routes/device.py`: `Depends(get_device_vehicle),,` — double comma.
3. **DB password lives in two places** — `alembic.ini` (committed to git) and `.env`. Patch makes Alembic read `DATABASE_URL` from `.env`, so the leaked `smartguard_pass` can be retired.

After the patch: all 7 migrations run on an empty DB through `a3c91e7d5b42`, the app boots, `/health` responds, `/api/device/key` returns 403 without login (correct).

Apply it on your laptop and push, so the repo is right:

```bash
cd anti_theft_app
git apply backend-fixes.patch
git commit -am "Fix broken imports, restore engine start command, fix httpx pin, alembic reads .env"
git push
```

(`setup.sh` also applies it on the server if the repo isn't fixed yet.)

> The earlier `event_recording_step1.patch` / `DEVICE_API_SECRET` design is **obsolete** — the committed version uses per-vehicle device keys in the DB (`POST /api/device/key`). Don't apply it, don't add `DEVICE_API_SECRET`.

## 2. Create the instance

- ECS, **2 vCPU / 4 GiB**, same region (Singapore) is fine.
- Image: **Ubuntu 24.04** (22.04 also works).
- 40 GB system disk is enough; media is purged after 30 days.
- Assign a public IP / EIP.
- Use a new security group (below), not the old one.

## 3. Security group (inbound)

| Protocol | Port (Alibaba format) | Source | Why |
|---|---|---|---|
| TCP | 22/22 | **your IP/32** | SSH |
| TCP | 80/80 | 0.0.0.0/0 | HTTP→HTTPS, cert renewal |
| TCP | 443/443 | 0.0.0.0/0 | API + WebSocket |
| TCP | 8883/8883 | 0.0.0.0/0 | MQTT over TLS (ESP32, simulator) |
| UDP | 3478/3478 | 0.0.0.0/0 | STUN/TURN |
| TCP | 3478/3478 | 0.0.0.0/0 | TURN over TCP |
| TCP | 5349/5349 | 0.0.0.0/0 | TURNS |
| UDP | 49160/49200 | 0.0.0.0/0 | TURN relay range |
| ICMP | -1/-1 | 0.0.0.0/0 | ping (optional) |

**Do not open** 1883, 8000, 3389 — your old group had all three open to the world. 1883 is unauthenticated plaintext and the backend never needs it externally; 8000 bypassed nginx/HTTPS; 3389 is Windows RDP. Your home IP changes? Use ECS Workbench for SSH instead of opening 22 to everyone.

## 4. Run the setup

Get a fresh Firebase key first: Firebase console → Project settings → Service accounts → *Generate new private key*, then **delete the old key** (it was pasted into a chat).

```bash
scp setup.sh backend-fixes.patch firebase_credentials.json root@<NEW_IP>:/root/vigilx/
ssh root@<NEW_IP>
cd /root/vigilx
DUCKDNS_TOKEN=<your token> CERT_EMAIL=<your email> bash setup.sh
```

It does, in order: packages → new random secrets (`/root/vigilx-secrets.env`) → DuckDNS points to the new IP + 5-min cron → PostgreSQL `smartguard` DB/user → Let's Encrypt cert → cert-copy hook for coturn/Mosquitto → Mosquitto (1883 localhost, 8883 TLS) → coturn with the new private/public IPs + `allowed-peer-ip` fix → clone + venv + `.env` + `alembic upgrade head` → systemd `vigilx` → nginx → health checks.

Safe to re-run; secrets are reused.

**Expected at the end:** all services `active`, `/health` shows `"mqtt_connected": true`, logs show `Firebase Admin initialized`, `MQTT connected`, `Subscribed to …`.

### If you rescued old data

Run the script first, then:

```bash
systemctl stop vigilx
sudo -u postgres dropdb smartguard && sudo -u postgres createdb -O smartguard smartguard
sudo -u postgres psql smartguard < smartguard.sql
cd /root/anti_theft_app/backend && venv/bin/alembic upgrade head
tar xzf media.tgz -C /
systemctl start vigilx
```

Old device keys keep working after a restore.

## 5. After setup

1. **Flutter app** — no rebuild needed if the domain stays `vigilx.duckdns.org`. Users are logged out (new `SECRET_KEY`); log in again (or register, on a fresh DB).
2. **Vehicle** — on a fresh DB, add the vehicle with the same `device_id` the firmware uses (e.g. `esp-001`).
3. **Camera device key** — logged in as the owner: `POST https://vigilx.duckdns.org/api/device/key` → put the returned key in the camera firmware. Returned once only.
4. **ESP32 + simulator** — update `MQTT_PASSWORD` (and `TURN_SECRET` for the simulator) from `/root/vigilx-secrets.env`. Host stays `vigilx.duckdns.org:8883`. Replace any hardcoded `47.236.73.110`.
5. **TURN check** — Trickle ICE page (from `docs/turn-server-setup.md`), look for a `relay` candidate.

## 6. Where my setup differs from the notes you pasted (on purpose)

| Notes said | Setup uses | Why |
|---|---|---|
| DB `vigilx_db` / user `vigilx` | `smartguard` / `smartguard` | That's what the repo and `alembic.ini` actually use |
| nginx `proxy_pass http://127.0.0.1:8000/;` | no trailing slash | With the slash, nginx strips `/api` and every route 404s — routes are mounted at `/api/...` |
| no `/health` location | added | Health check was unreachable through nginx |
| uvicorn `--host 0.0.0.0` | `127.0.0.1` | Port 8000 shouldn't be reachable from outside |
| Mosquitto reads `/etc/letsencrypt/live/…` | copies to `/etc/mosquitto/certs` | Mosquitto runs as `mosquitto` and can't read root-only private keys; hook keeps copies fresh on renewal |
| coturn certs `/etc/turn_certs` | `/etc/turnserver/certs` | Matches `docs/turn-server-setup.md` |
| Port 8883 "not used" | open | Simulator and ESP32 connect to it with TLS |
| `pip install python-multipart` manually | already in `requirements.txt` | — |

## 7. Troubleshooting

| Symptom | Check |
|---|---|
| `vigilx` keeps restarting | `journalctl -u vigilx -n 50` — usually missing `firebase_credentials.json` or `.env` key |
| `mqtt_connected: false` | `MQTT_PASSWORD` in `.env` vs `mosquitto_passwd`; `journalctl -u mosquitto` |
| Video fails on mobile data | `tail /var/log/turnserver.log`; `403 Forbidden IP` → `allowed-peer-ip` wrong; `508` → `external-ip` wrong; UDP 49160–49200 not open |
| Clip upload 413 | nginx `client_max_body_size` in `/api/device/` block |
| Cert renewal | `certbot renew --dry-run` |

Logs: `journalctl -u vigilx -f`.
