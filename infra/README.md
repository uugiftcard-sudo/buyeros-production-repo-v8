# Infrastructure

此目錄保存 BuyerOS 部署和基礎設施輔助檔案。

## Supabase

先在 Supabase SQL editor 執行：

```sql
-- infra/agent_memory.sql
```

這會建立 `agent_memory` 以及 namespace/key 索引。

## VPS Deploy

在本地準備 `.env.production`，建議由 template 開始：

```bash
cp .env.production.template .env.production
python backend/scripts/validate_env.py --env .env.production
```

填好後：

```bash
chmod +x infra/deploy_vps.sh infra/set_telegram_webhook.sh
infra/deploy_vps.sh root@206.189.116.155 /opt/buyeros .env.production
```

腳本會用 `rsync` 上傳專案、複製 env file 到 VPS 的 `.env`，並執行：

```bash
docker compose up -d --build
```

Redis 只在 Docker network 內暴露給 backend，不應直接開到公網。

部署後跑 smoke：

```bash
infra/smoke_api.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY"
infra/smoke_telegram_webhook.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" "$TELEGRAM_WEBHOOK_SECRET"
infra/go_live_audit.sh .env.production.local "$PUBLIC_BASE_URL" root@206.189.116.155 root@167.172.60.38
```

Ops drill after deploy:

```bash
infra/run_ops_drill.sh \
  .env.production.local \
  https://buyeros.206.189.116.155.sslip.io \
  http://167.172.60.38:8000 \
  root@206.189.116.155
```

This always syncs backup/failover summaries to the primary release so
`/ops/status` shows the latest successful or failed drill.

Staging-only rollback drill:

```bash
infra/run_staging_rollback_drill.sh \
  .env.production.local \
  root@167.172.60.38 \
  root@206.189.116.155
```

Rollback is performed only on staging. The rollback summary is synced to the
primary release for `/ops/status` visibility.

`smoke_api.sh` 會先驗證核心 API / context / dispatcher，然後自動驗證三條
canonical 工作線：`buyer_ai`、`commerce`、`xau`。

邊界：
- `buyer_ai`：BuyerOS / AI Team / 買手 Report / sourcing ROI / refund reconciliation / OCR posting / manual review / shared memory / Telegram
- `commerce`：webshop order / after-sales / payment / inventory / support / shop finance / live selling；only supplies commerce source data for `buyer_ai` reconciliation
- `xau`：XAU AI live stream / news / script generation / OBS / promo / conversion / metrics

一條命令全流程（後端 + UI）：

```bash
infra/smoke_one_click.sh --local .env.production.local
```

已安裝 Docker 時可直接用 Docker 模式：

```bash
infra/smoke_one_click.sh --docker .env.production.local
```

`smoke_telegram_webhook.sh` 不會設定 Telegram webhook；它用 Telegram
update payload 直接打 `/telegram/webhook`，再用 `/context/session` 驗證退款
記憶可召回。正式 Telegram 上線仍要 HTTPS domain。

如只想跑核心 API：

```bash
BUYEROS_SKIP_THREE_SYSTEMS_SMOKE=1 infra/smoke_api.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY"
```

臨時 staging 如果使用 `sslip.io` 且 Let's Encrypt 對 `sslip.io` 觸發 rate
limit，Caddy 可能只能取得不被 browser 信任的 staging certificate。這時只
能用 staging smoke 驗證功能，不應當作 production HTTPS ready：

```bash
BUYEROS_CURL_INSECURE=1 infra/smoke_api.sh "https://buyeros.167.172.60.38.sslip.io" "$BUYEROS_API_KEY"
```

若 DigitalOcean Cloud Firewall 未放行 `80/443`，可先用 backend direct
port 驗證 staging app：

```bash
infra/smoke_api.sh "http://167.172.60.38:8000" "$BUYEROS_API_KEY"
```

Production 不應使用 `BUYEROS_CURL_INSECURE=1`。正式上線要使用自己控制的
domain，並在 DigitalOcean Firewall 放行 inbound TCP `80` 和 `443`。

上線前 24 小時穩定性 smoke：

```bash
infra/smoke_24h.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" 24 3600
```

如要先做短測：

```bash
infra/smoke_24h.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" 1 300
```

三系統由本地、staging、production 到 Telegram 的完整上線計劃：

```text
docs/THREE_WORKSPACE_GO_LIVE_PLAN.md
```

一條命令部署並驗收 staging：

```bash
infra/deploy_and_smoke.sh root@167.172.60.38 /opt/buyeros .env.production.local "$STAGING_BASE_URL"
```

一條命令部署並驗收 production，部署前先備份：

```bash
infra/deploy_and_smoke.sh root@206.189.116.155 /opt/buyeros .env.production.local "$PUBLIC_BASE_URL" --backup-before
```

雙 VPS 拓撲請見：

```text
docs/DEPLOY_TOPOLOGY.md
```

## VPS Cleanup (recommended before first deploy)

先盤點再清理，避免誤刪：

```bash
chmod +x infra/audit_vps.sh infra/cleanup_vps.sh
infra/audit_vps.sh root@206.189.116.155
infra/audit_vps.sh root@167.172.60.38
```

先 dry-run：

```bash
infra/cleanup_vps.sh root@206.189.116.155
infra/cleanup_vps.sh root@167.172.60.38
```

確認後才執行真正清理：

```bash
infra/cleanup_vps.sh root@206.189.116.155 --execute --keep-path /opt/buyeros
infra/cleanup_vps.sh root@167.172.60.38 --execute --keep-path /opt/buyeros
```

上線前 `.env.production` 至少應包含：

```bash
SUPABASE_URL=
SUPABASE_KEY=
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
PUBLIC_BASE_URL=https://YOUR_DOMAIN
BUYEROS_DOMAIN=YOUR_DOMAIN
REDIS_URL=redis://redis:6379/0
BUYEROS_API_KEY=
OPENROUTER_API_KEY=
```

## HTTPS

Docker Compose 會啟動 Caddy，並用 `BUYEROS_DOMAIN` 申請 HTTPS。沒有正式
domain 時，可先用 `sslip.io`：

```bash
BUYEROS_DOMAIN=buyeros.206.189.116.155.sslip.io
PUBLIC_BASE_URL=https://buyeros.206.189.116.155.sslip.io
```

Caddy 會把 HTTPS 流量反代到 backend `:8000`。

`sslip.io` 是共享 wildcard domain，Let's Encrypt 可能因其他使用者觸發
rate limit。若 staging HTTPS 只差可信憑證，請改用自有 staging domain，
例如 `staging.YOUR_DOMAIN` 指向 `167.172.60.38`，再重 deploy。

## Telegram

HTTPS domain ready 後：

```bash
infra/set_telegram_webhook.sh "$TELEGRAM_BOT_TOKEN" https://YOUR_DOMAIN
```

如果設定了 `TELEGRAM_WEBHOOK_SECRET`，用：

```bash
infra/set_telegram_webhook.sh "$TELEGRAM_BOT_TOKEN" https://YOUR_DOMAIN "$TELEGRAM_WEBHOOK_SECRET"
```

`set_telegram_webhook.sh` 會先用 Telegram `getMe` 驗證 bot token；如果
token 已 revoke 或貼錯，會停低並提示刷新 `TELEGRAM_BOT_TOKEN`。
