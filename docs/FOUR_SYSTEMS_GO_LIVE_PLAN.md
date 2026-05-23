# BuyerOS 四個系統 Go-Live Plan

## Canonical Systems

| System | Canonical lane | Scope |
| --- | --- | --- |
| 買手 Report | `report` | 日報 / 週報 / CSV export / 毛利、退款、異常摘要 |
| 網店自動系統 | `commerce` | 退款 / OCR 入帳 / 對帳 / 差異告警 / retry queue |
| XAU Promo | `xau` | Campaign / conversion / metrics / UTM / revenue |
| AI 一人公司 Team | `ai_team` | Context Hub / Provider fallback / Task Dispatcher / Memory Timeline |

Aliases are accepted only at the API boundary:

- `buyeros -> ai_team`
- `cloth -> commerce`
- `shop -> commerce`
- `promo -> xau`
- `xau_promo -> xau`

## P0 Verification

Run from the repository root:

```bash
./.venv/bin/python -m pytest -q
./.venv/bin/python -m compileall -q backend/app
./.venv/bin/python backend/scripts/validate_env.py --env .env.production.local
```

Frontend:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit
./node_modules/.bin/next build
./node_modules/.bin/playwright test
cd ..
```

Runtime:

```bash
bash infra/smoke_api.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY"
bash infra/smoke_four_systems.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY"
bash infra/smoke_telegram_webhook.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" "$TELEGRAM_WEBHOOK_SECRET"
bash infra/go_live_audit.sh .env.production.local "$PUBLIC_BASE_URL" root@206.189.116.155 root@167.172.60.38
```

`smoke_four_systems.sh` proves:

- `/projects` returns exactly `report / commerce / xau / ai_team`
- `/tasks` contains all four canonical lanes
- Report can create/history/export a daily report
- Commerce can process `退款 991` then recall `991 點？`
- XAU can create a campaign, record conversion, and return metrics
- AI Team can create a dispatch plan, run all subtasks, and write routing/run_all timeline records

`smoke_telegram_webhook.sh` proves the FastAPI webhook path without relying on
Telegram delivery: webhook update -> workflow -> memory -> session recall.

## Deployment Order

1. Run local P0 verification.
2. Deploy staging VPS and run `infra/smoke_api.sh`.
3. Run stability smoke:

   ```bash
   bash infra/smoke_24h.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" 24 3600
   ```

4. Deploy production:

   ```bash
   bash infra/deploy_and_smoke.sh root@206.189.116.155 /opt/buyeros .env.production.local "$PUBLIC_BASE_URL" --backup-before
   ```

5. Configure HTTPS with Caddy. For a temporary production-grade URL before a
   purchased domain is ready, use:

   ```bash
   BUYEROS_DOMAIN=buyeros.206.189.116.155.sslip.io
   PUBLIC_BASE_URL=https://buyeros.206.189.116.155.sslip.io
   ```

6. Set Telegram webhook:

   ```bash
   bash infra/set_telegram_webhook.sh "$TELEGRAM_BOT_TOKEN" "$PUBLIC_BASE_URL" "$TELEGRAM_WEBHOOK_SECRET"
   ```

7. Manually send Telegram messages:

   ```text
   退款 991
   991 點？
   ```

Expected: the second message recalls the persisted refund memory.

## Current External Gates

- Staging VPS must accept SSH before staging deploy can be verified.
- Real Telegram webhook requires a Telegram-accepted bot token. The HTTPS
  endpoint can be smoke-tested with `infra/smoke_telegram_webhook.sh`; if
  `infra/set_telegram_webhook.sh` returns `Unauthorized`, refresh
  `TELEGRAM_BOT_TOKEN` from BotFather and retry.
