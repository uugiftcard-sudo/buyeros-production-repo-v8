# BuyerOS Deploy Topology

## Goal

Use both VPS machines without making production routing ambiguous.

## Node Roles

### Primary Node

- Host: `206.189.116.155`
- Droplet: `ubuntu-s-4vcpu-8gb-lon1-01`
- Purpose: production BuyerOS

Run on this node:

- FastAPI backend
- Redis
- Next.js admin UI
- Telegram webhook
- OpenRouter/provider routing
- production Context Hub
- production audit trail
- business automation API

Why:

- more CPU and RAM headroom
- safer for Telegram + Redis + provider calls
- better place for future workers or dashboard

### Secondary Node

- Host: `167.172.60.38`
- Droplet: `ubuntu-s-1vcpu-2gb-70gb-intel-lon1-01`
- Purpose: support / staging / ops

Use this node for one of:

- staging BuyerOS
- reverse proxy or relay
- health checks / cron / lightweight monitoring
- backup deployment target
- manual failover smoke target

Current staging fallback:

- App smoke can use `http://167.172.60.38:8000`.
- Temporary HTTPS can use `BUYEROS_CURL_INSECURE=1` with
  `https://buyeros.167.172.60.38.sslip.io` when `sslip.io` ACME rate limits
  prevent a trusted certificate.
- For trusted staging browser access, use a real staging domain and allow
  inbound TCP `80` and `443` in the DigitalOcean firewall.

Do not use it as a second live Telegram production webhook target at the same time.

## Traffic Flow

```text
Telegram
  -> HTTPS domain
  -> Primary VPS (206.189.116.155)
  -> FastAPI /telegram/webhook
  -> BuyerOSGraphWorkflow
  -> Redis + Supabase
  -> Telegram reply
```

Optional support path:

```text
Operator / Admin
  -> Secondary VPS
  -> staging / health checks / proxy tools
```

## Deployment Policy

- Production deploys go to primary node by default.
- Staging or experiments go to secondary node.
- `.env.production` is for primary node.
- If needed later, create a separate `.env.staging` for secondary node.

## Current Recommendation

1. Use `206.189.116.155` as the first production target.
2. Keep `167.172.60.38` for staging or ops support.
3. Bind the final HTTPS domain only to the primary node first.
4. Set Telegram webhook only after primary HTTPS is live.
5. Run `infra/smoke_api.sh` after every deploy.
6. Run `infra/backup_vps.sh` before risky changes and keep the archive path for rollback.
