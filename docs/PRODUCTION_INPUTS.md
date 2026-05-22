# BuyerOS Production Inputs

Fill this page before deployment. Do not commit real secrets to GitHub.

## VPS

### Primary VPS

| Field | Value |
| --- | --- |
| Role | `production app server` |
| SSH target | `root@206.189.116.155` |
| Remote directory | `/opt/buyeros` |
| Domain | `TODO_HTTPS_DOMAIN` |
| Droplet name | `ubuntu-s-4vcpu-8gb-lon1-01` |
| Project | `first-project` |
| Region | `LON1` |
| Size | `8 GB / 4 vCPU` |
| OS | `Ubuntu 24.04 (LTS) x64` |
| Docker installed | yes/no |
| Caddy or Nginx installed | yes/no |

### Secondary VPS

| Field | Value |
| --- | --- |
| Role | `staging / proxy / ops helper` |
| SSH target | `root@167.172.60.38` |
| Remote directory | `/opt/buyeros` |
| Domain | optional |
| Droplet name | `ubuntu-s-1vcpu-2gb-70gb-intel-lon1-01` |
| Region | `LON1` |
| Size | `2 GB / 1 Intel vCPU / 70 GB` |
| OS | `Ubuntu 24.04 (LTS) x64` |
| Docker installed | yes/no |
| Caddy or Nginx installed | yes/no |

## Supabase

Run `infra/agent_memory.sql` in Supabase first.

| Field | Value |
| --- | --- |
| `SUPABASE_URL` | `TODO_SUPABASE_URL` |
| `SUPABASE_KEY` | `TODO_SUPABASE_SERVICE_ROLE_OR_ANON_KEY` |
| `agent_memory` table created | yes/no |

## Telegram

| Field | Value |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | `TODO_TELEGRAM_BOT_TOKEN` |
| `TELEGRAM_WEBHOOK_SECRET` | generated in `.env.production` |
| Webhook URL | `TODO_HTTPS_DOMAIN/telegram/webhook` |

After deploy:

```bash
infra/set_telegram_webhook.sh "$TELEGRAM_BOT_TOKEN" https://YOUR_DOMAIN "$TELEGRAM_WEBHOOK_SECRET"
```

## BuyerOS API

| Field | Value |
| --- | --- |
| `BUYEROS_API_KEY` | generated in `.env.production` |
| Health URL | `TODO_HTTPS_DOMAIN/health/ready` |
| Provider status URL | `TODO_HTTPS_DOMAIN/providers` |

API calls should include one of:

```bash
X-Buyeros-Api-Key: YOUR_KEY
Authorization: Bearer YOUR_KEY
```

## OpenRouter / Providers

| Field | Value |
| --- | --- |
| `OPENROUTER_API_KEY` | `TODO_OPENROUTER_API_KEY` |
| Supervisor model | `openai/gpt-4o-mini` |
| Claude/Cursor model | `anthropic/claude-3.5-sonnet` |
| Gemini model | `google/gemini-pro-1.5` |
| DeepSeek model | `deepseek/deepseek-chat` |
| MiniMax model | `minimax/minimax-01` |
| Grok model | `x-ai/grok-2` |
| Perplexity model | `perplexity/sonar` |

## Business Integrations

| Field | Value |
| --- | --- |
| `PAYMENT_GATEWAY_BASE_URL` | optional |
| `PAYMENT_GATEWAY_API_KEY` | optional |
| `OCR_SPACE_API_KEY` | optional |
| `OCR_API_URL` | default `https://api.ocr.space/parse/image` |
| `FINANCE_API_BASE_URL` | optional |
| `FINANCE_API_KEY` | optional |

## Deploy Commands

```bash
cp .env.production.template .env.production
# fill .env.production
python backend/scripts/validate_env.py --env .env.production
infra/deploy_vps.sh root@206.189.116.155 /opt/buyeros .env.production
```

## Post-Deploy Checks

```bash
curl https://YOUR_DOMAIN/ping
curl https://YOUR_DOMAIN/health/ready
curl -H "Authorization: Bearer $BUYEROS_API_KEY" https://YOUR_DOMAIN/providers
curl -H "Authorization: Bearer $BUYEROS_API_KEY" https://YOUR_DOMAIN/system/capabilities
bash infra/smoke_api.sh https://YOUR_DOMAIN "$BUYEROS_API_KEY"
```

## Ops Automation

```bash
infra/preflight_deploy.sh .env.production
infra/backup_vps.sh root@206.189.116.155 /opt/buyeros /opt/buyeros-backups
infra/rollback_vps.sh root@206.189.116.155 /opt/buyeros-backups/<archive>.tgz /opt/buyeros
infra/failover_smoke.sh https://PRIMARY_DOMAIN https://SECONDARY_DOMAIN "$BUYEROS_API_KEY" 300
```

## Deployment Choice

- Primary VPS should run the real BuyerOS production stack.
- Secondary VPS should be used for staging, proxy, backup relay, or ops tasks.
- Do not point Telegram production webhook at both machines at the same time.
