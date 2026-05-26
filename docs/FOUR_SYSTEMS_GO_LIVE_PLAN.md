# BuyerOS 三線 Go-Live Plan

## Canonical Systems

| System | Canonical lane | Scope |
| --- | --- | --- |
| 買手 AI 中樞 | `buyer_ai` | BuyerOS / AI Team / Context Hub / Telegram / 買手 Report / 退款 / OCR 入帳 / 對帳 / 採購 ROI / supplier / lead / manual review |
| 網店自動系統 | `commerce` | AI 虛擬主播帶貨 / 訂單 / 庫存 / 客服 / 網店收支報表 / Shopify / TikTok / 網店資料同步 |
| XAU 系統 | `xau` | AI 直播 / 虛擬主播 / Campaign / conversion / metrics / UTM / revenue |

Aliases are accepted only at the API boundary:

- `buyeros -> buyer_ai`
- `ai_team -> buyer_ai`
- `buyer_report -> buyer_ai`
- `report -> buyer_ai`
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

`smoke_four_systems.sh` is kept for compatibility, but should prove three canonical lines:

- `/projects` returns exactly `buyer_ai / commerce / xau`
- `/tasks` normalizes legacy aliases into the three canonical lanes
- Buyer AI can create/history/export a buyer report, run sourcing ROI tasks, and process `退款 991` then recall `991 點？`
- Commerce can handle AI livestream selling flows, shop orders, inventory, support, shop revenue/expense reports, Shopify/TikTok sync, and supply webshop source data to `buyer_ai`
- XAU can run AI livestream/campaign funnel tracking, create a campaign, record conversion, and return metrics
- AI Team behavior is represented under `buyer_ai`: dispatch plan, run_all subtasks, routing/run_all timeline records

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
