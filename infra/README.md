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
python backend/scripts/validate_env.py .env.production
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
REDIS_URL=redis://redis:6379/0
BUYEROS_API_KEY=
OPENROUTER_API_KEY=
```

## HTTPS

用 Caddy 或 Nginx 在 VPS 做 TLS termination，再反代到
`127.0.0.1:8000`。`infra/Caddyfile.example` 是最小 Caddy 範本。

## Telegram

HTTPS domain ready 後：

```bash
infra/set_telegram_webhook.sh "$TELEGRAM_BOT_TOKEN" https://YOUR_DOMAIN
```

如果設定了 `TELEGRAM_WEBHOOK_SECRET`，用：

```bash
infra/set_telegram_webhook.sh "$TELEGRAM_BOT_TOKEN" https://YOUR_DOMAIN "$TELEGRAM_WEBHOOK_SECRET"
```
