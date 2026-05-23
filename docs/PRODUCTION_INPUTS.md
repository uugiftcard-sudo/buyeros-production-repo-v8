# BuyerOS Production Inputs

> ⚠️ **DO NOT commit real secrets to GitHub.** Use `.env.production` (gitignored) or your
> deployment tool's secret manager (e.g. DigitalOcean App Platform secrets, GitHub Actions secrets).
> Run `python backend/scripts/validate_env.py --env .env.production` before deploying.

## Step 1 — VPS Setup

### Primary VPS
| Field | Value |
| --- | --- |
| Role | `production app server` |
| SSH target | `root@206.189.116.155` |
| Remote directory | `/opt/buyeros` |
| Domain | *(fill after purchasing — see Step 3)* |
| Droplet name | `ubuntu-s-4vcpu-8gb-lon1-01` |
| Region | LON1 |
| Size | 8 GB / 4 vCPU |
| OS | Ubuntu 24.04 LTS |

### Secondary VPS
| Field | Value |
| --- | --- |
| Role | `staging / failover / ops helper` |
| SSH target | `root@167.172.60.38` |
| Remote directory | `/opt/buyeros` |
| Domain | optional |
| Region | LON1 |
| Size | 2 GB / 1 Intel vCPU |

> **Firewall:** Confirm TCP 80 is open on both Droplets (DigitalOcean Cloud Firewall → Networking → Firewalls → inbound HTTP/80). This is required for Caddy Let's Encrypt HTTP-01 challenges and automatic HTTPS renewal.

---

## Step 2 — Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Run `infra/agent_memory.sql` in the Supabase SQL editor
3. Find your URL and keys in **Settings → API**

| Field | Value |
| --- | --- |
| `SUPABASE_URL` | `https://xxxxx.supabase.co` |
| `SUPABASE_KEY` | Service role key (keep server-side only) |
| `agent_memory` table created | ✅ done |

---

## Step 3 — Domain & HTTPS

1. Point your domain's A record to `206.189.116.155`
2. Set `BUYEROS_DOMAIN=your-domain.com` in `.env.production`
3. Caddy (in `docker-compose.yml`) will automatically provision and renew HTTPS via Let's Encrypt

> Without a real domain, you can use `https://buyeros.206.189.116.155.sslip.io` as a temporary SSL endpoint (sslip.io auto-generates TLS certs).

---

## Step 4 — Telegram Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram → `/newbot`
2. Copy the bot token
3. After deploy, set the webhook:

```bash
# After BuyerOS is live at your HTTPS domain:
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook" \
  -d url=https://YOUR_DOMAIN/telegram/webhook
```

| Field | Value |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | `7xxxxxxxxxx:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TELEGRAM_WEBHOOK_SECRET` | Generate with `openssl rand -hex 32` |
| Webhook URL | `https://YOUR_DOMAIN/telegram/webhook` |

---

## Step 5 — OpenRouter / AI Providers

Get a key at [openrouter.ai](https://openrouter.ai). All provider adapters route through OpenRouter in v1.

| Field | Value |
| --- | --- |
| `OPENROUTER_API_KEY` | `sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxxxx` |
| Supervisor model | `openai/gpt-4o-mini` |
| Claude fallback model | `anthropic/claude-sonnet-4.5` |

> The `OPENROUTER_MODEL_*` env vars (e.g. `OPENROUTER_MODEL_CLAUDE`) can override per-provider models.

---

## Step 6 — Business Integrations (Optional)

| Field | Required | Notes |
| --- | --- | --- |
| `PAYMENT_GATEWAY_BASE_URL` | No | Stripe/PayPal/custom base URL |
| `PAYMENT_GATEWAY_API_KEY` | No | Payment gateway API key |
| `OCR_SPACE_API_KEY` | No | [ocr.space](https://ocr.space) free tier available |
| `FINANCE_API_BASE_URL` | No | Your accounting system API |
| `FINANCE_API_KEY` | No | |

---

## Step 7 — Deployment Checklist

```bash
# 1. Copy and fill production env
cp .env.example .env.production
nano .env.production    # fill all TODOs above

# 2. Validate all required vars are present
python backend/scripts/validate_env.py --env .env.production

# 3. Deploy to primary VPS
bash infra/deploy_vps.sh root@206.189.116.155 /opt/buyeros .env.production

# 4. Verify
curl https://YOUR_DOMAIN/ping
curl -H "Authorization: Bearer $BUYEROS_API_KEY" https://YOUR_DOMAIN/health/ready
curl -H "Authorization: Bearer $BUYEROS_API_KEY" https://YOUR_DOMAIN/providers
bash infra/smoke_api.sh https://YOUR_DOMAIN "$BUYEROS_API_KEY"
```

---

## Production Readiness Gate

Run all of these before going live:

```bash
python backend/scripts/validate_env.py --env .env.production
bash infra/smoke_api.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY"
bash infra/smoke_telegram_webhook.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" "$TELEGRAM_WEBHOOK_SECRET"
bash infra/smoke_24h.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" 24 3600
```

---

## Missing / Gaps Tracker

Use this table to track what's still TODO:

| Item | Status | Notes |
| --- | --- | --- |
| Production domain purchased | ⬜ | Required for real HTTPS |
| Supabase configured | ⬜ | Required for persistent memory |
| TCP 80 firewall open | ⬜ | Required for Caddy Let's Encrypt |
| Telegram bot created | ⬜ | Required for live Telegram integration |
| OpenRouter API key | ⬜ | Required for AI routing |
| Hermes provider implemented | ⬜ | Currently a stub — ships as `not_configured` |
| Real payment gateway | ⬜ | Stripe/PayPal adapter code exists |
| Real Google Sheets | ⬜ | Adapter code exists, needs credentials |
| Scheduler / cron | ⬜ | Daily reports triggered manually via API |
