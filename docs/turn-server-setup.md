# TURN Server Setup (coturn)

## Why this exists

WebRTC video (used for the camera streaming feature) needs a way for the
phone and the camera device to exchange video when a direct connection
isn't possible — which is the common case here, since the camera device
sits behind cellular carrier NAT (via the SIM7670E) and phones sit behind
mobile/WiFi NAT. TURN is the relay server that makes the connection work
reliably in both cases, instead of "works sometimes, fails mysteriously
other times."

This runs as `coturn` directly on the same Alibaba Cloud ECS box as the
rest of the backend (`47.236.73.110` / `vigilx.duckdns.org`).

## Install

```bash
sudo apt update
sudo apt install -y coturn
sudo sed -i 's/^#TURNSERVER_ENABLED=1/TURNSERVER_ENABLED=1/' /etc/default/coturn
```

## Auth model

coturn uses a **shared secret**, not fixed usernames/passwords. The
backend generates short-lived, per-session credentials from this secret
(HMAC-signed, expiring after ~1 hour); coturn validates them
independently using the same secret, without storing anything itself.

Generate the secret:
```bash
openssl rand -hex 32
```
This value is stored in `/etc/turnserver.conf` as `static-auth-secret`,
and must also be set in the backend's `.env` as `TURN_SECRET` (see Step 3
of the camera-streaming build) so the backend can mint matching
credentials. **The secret should never be committed to the repo** — it
lives only in `/etc/turnserver.conf` and `backend/.env`, both untracked.

## Config — `/etc/turnserver.conf`

```ini
listening-port=3478
tls-listening-port=5349

# ── NAT handling ──────────────────────────────────────────────────────────
# Alibaba Cloud NATs the public IP onto the box's real private interface —
# coturn must bind sockets on the private IP but advertise the public IP
# to clients, or relay allocation fails with "508 Cannot create socket".
listening-ip=172.18.65.233
external-ip=47.236.73.110/172.18.65.233
relay-ip=172.18.65.233

min-port=49160
max-port=49200

realm=vigilx.duckdns.org
server-name=vigilx.duckdns.org

use-auth-secret
static-auth-secret=<SECRET — see backend/.env TURN_SECRET, never commit the real value>
lt-cred-mech

cert=/etc/turnserver/certs/fullchain.pem
pkey=/etc/turnserver/certs/privkey.pem
no-tlsv1
no-tlsv1_1

# ── Security: block relaying to internal/private addresses ─────────────────
# Prevents this TURN server from being abused as a pivot into this box's
# own VPC or Alibaba Cloud's internal metadata service.
denied-peer-ip=10.0.0.0-10.255.255.255
denied-peer-ip=172.16.0.0-172.31.255.255
denied-peer-ip=192.168.0.0-192.168.255.255
denied-peer-ip=127.0.0.0-127.255.255.255
denied-peer-ip=100.100.100.200-100.100.100.200

no-multicast-peers
no-cli
fingerprint
log-file=/var/log/turnserver.log
verbose
```

> Note: `denied-peer-ip` blocks `172.16.0.0/12`, which includes this box's
> own private IP. That's expected and correct — it only affects a peer
> *inside* that range (like the server testing against itself with
> `turnutils_uclient`), never a real phone or camera on the public
> internet.

## TLS cert — kept in sync with Let's Encrypt automatically

coturn's own user can't read the main nginx cert (root-only), so a copy is
kept in `/etc/turnserver/certs/` and refreshed on every renewal:

```bash
sudo mkdir -p /etc/turnserver/certs
sudo tee /etc/letsencrypt/renewal-hooks/deploy/turnserver-cert.sh << 'EOF'
#!/bin/bash
cp /etc/letsencrypt/live/vigilx.duckdns.org/fullchain.pem /etc/turnserver/certs/fullchain.pem
cp /etc/letsencrypt/live/vigilx.duckdns.org/privkey.pem /etc/turnserver/certs/privkey.pem
chown turnserver:turnserver /etc/turnserver/certs/*.pem
chmod 600 /etc/turnserver/certs/*.pem
systemctl restart coturn
EOF
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/turnserver-cert.sh
sudo /etc/letsencrypt/renewal-hooks/deploy/turnserver-cert.sh
```

## Alibaba Cloud Security Group rules

Console → ECS instance → Security Groups → Configure Rules → Add Rule.
**Port ranges use `/` as the separator, not `-`** (e.g. `49160/49200`).

| Protocol | Port range    | Source    |
|----------|---------------|-----------|
| UDP      | 3478/3478     | 0.0.0.0/0 |
| TCP      | 3478/3478     | 0.0.0.0/0 |
| TCP      | 5349/5349     | 0.0.0.0/0 |
| UDP      | 49160/49200   | 0.0.0.0/0 |

If `ufw` is active on the box itself, mirror the same rules there:
```bash
sudo ufw allow 3478
sudo ufw allow 5349/tcp
sudo ufw allow 49160:49200/udp
```

## Start it

```bash
sudo systemctl enable --now coturn
sudo systemctl status coturn
```

Logs go to journald, not the configured `log-file` (the service is
sandboxed without write access there) — use:
```bash
sudo journalctl -u coturn -f
```

## Verifying it works

Generate a test credential pair:
```bash
python3 -c "
import hmac, hashlib, base64, time
secret = '<TURN_SECRET>'
username = str(int(time.time()) + 3600)
credential = base64.b64encode(hmac.new(secret.encode(), username.encode(), hashlib.sha1).digest()).decode()
print(username)
print(credential)
"
```

**Local test** (proves auth + allocation work, but the "peer" is the
server's own private network, so expect a `403 Forbidden IP` on channel
bind — that's the denied-peer-ip rule correctly blocking a same-machine
test, not a real failure):
```bash
turnutils_uclient -v -u <username> -w <credential> vigilx.duckdns.org
```
Success looks like repeated `allocate response received: success` and a
`Received relay addr: 47.236.73.110:<port>` in the 49160–49200 range.

**Real external test** — https://webrtc.github.io/samples/src/content/peerconnection/trickle-ice/
- Remove any default TURN entries
- Add server: URL `turn:vigilx.duckdns.org:3478`, username/credential from
  above
- Set `IceTransports` to `relay` (forces only relay candidates — if one
  appears, TURN is fully working end to end; if the list is empty, it's
  failing)
- Click "Gather candidates" — expect a `relay` row, `relayProtocol: udp`,
  address `47.236.73.110`, port in the opened range

## Rotating the secret

```bash
openssl rand -hex 32
```
Update `static-auth-secret` in `/etc/turnserver.conf` **and**
`TURN_SECRET` in `backend/.env` together, then:
```bash
sudo systemctl restart coturn
sudo systemctl restart vigilx
```