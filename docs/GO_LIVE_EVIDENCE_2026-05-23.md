# BuyerOS Go-Live Evidence - 2026-05-23

## Release

- Main commit: `dcb4d51ef9eca2430b897ebc25196173ba3b7ff4`
- Production host: `206.189.116.155`
- Staging / failover host: `167.172.60.38`
- Active production release: `/opt/buyeros/releases/20260523035856`
- Production HTTPS URL: `https://buyeros.206.189.116.155.sslip.io`
- Direct fallback API: `http://206.189.116.155:8000`
- Direct fallback UI: `http://206.189.116.155:3000`

## Verified Checks

- Production health passed on direct API and HTTPS.
- Production full smoke passed with session `smoke-20260523044858`.
- Post-rollback production smoke passed with session `smoke-20260523045046`.
- Telegram webhook mock smoke passed for chat/session `991003`.
- Telegram webhook is set to `https://buyeros.206.189.116.155.sslip.io/telegram/webhook`.
- Telegram webhook info returned pending updates `0` and no last error.

## Ops Evidence

- Latest primary backup:
  - archive: `/opt/buyeros-backups/buyeros-20260523045014.tgz`
  - started: `2026-05-23T03:50:14Z`
  - ended: `2026-05-23T03:50:18Z`
  - duration: `4s`
- Latest primary rollback drill:
  - source: `/opt/buyeros-backups/buyeros-20260523045014.tgz`
  - started: `2026-05-23T03:50:22Z`
  - ended: `2026-05-23T03:50:28Z`
  - duration: `6s`
- Latest failover smoke:
  - target: `http://167.172.60.38:8000`
  - started: `2026-05-23T03:50:45Z`
  - ended: `2026-05-23T03:52:01Z`
  - RTO: `76s`
  - RPO: `27s`
- Latest smoke summary:
  - target: `https://buyeros.206.189.116.155.sslip.io`
  - started: `2026-05-23T03:54:27Z`
  - ended: `2026-05-23T03:55:56Z`
  - checks passed: `1`
  - checks failed: `0`

## 24h Watch

- 24h production watch started on the primary host.
- PID file: `/opt/buyeros/current/infra/.smoke_24h_pid`
- Log file: `/opt/buyeros/current/infra/smoke_24h-production.log`
- Command is configured to read `BUYEROS_API_KEY` from environment and uses `-` in argv so the key is not exposed in long-running process listings.

## Public Entrypoint Notes

- Caddy listens on `80`, `443`, `8000`, and `3000` on the production host.
- Droplet-local firewall (`ufw`) is inactive and iptables default input policy is ACCEPT.
- External HTTPS to `https://buyeros.206.189.116.155.sslip.io/ping` works.
- External direct API `http://206.189.116.155:8000/ping` works.
- External direct UI `http://206.189.116.155:3000` works.
- External plain HTTP `http://206.189.116.155/ping` did not connect during diagnosis.
- Current risk: TCP `80` appears blocked outside the droplet, likely DigitalOcean Cloud Firewall or upstream network policy. This does not block Telegram because Telegram is using HTTPS.

## Follow-Up

- Confirm DigitalOcean Cloud Firewall inbound TCP `80` rule.
- Let the 24h watch finish and review `smoke-latest.json`.
- Keep Telegram pointed only to production HTTPS; do not point it at the failover node unless performing a controlled cutover.
