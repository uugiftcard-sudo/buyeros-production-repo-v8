# Three Workspace Go-Live Plan (BuyerOS)

核心對象：
- `buyeros`（AI 團隊 / Context Hub）
- `cloth`（CLOTH 網店流程）
- `xau`（XAU 中控）

## 目標
- backend `/ping`、`/health/ready`、Provider、Context、Task 能通
- 一鍵部署主/副機，主機可在健康檢查後切換
- 前端管理台可完成任務派工、Run All、Timeline 查詢

## 上線步驟
1. 兩台 VPS 皆完成 `infra/deploy_vps.sh` 與 `docker compose up -d --build`
2. 配置 `.env.production`，並 run：
   - `python backend/scripts/validate_env.py --env .env.production`
3. 執行主機 smoke：
   - `BUYEROS_SKIP_THREE_SYSTEMS_SMOKE=1 infra/smoke_api.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY"`
4. 執行 frontend smoke：
   - `cd frontend && npm run ui:smoke`
5. 執行 Telegram webhook smoke：
   - `infra/smoke_telegram_webhook.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" "$TELEGRAM_WEBHOOK_SECRET"`
6. 綁定副機：
   - 主機故障時切到 `167.172.60.38`，確認服務可接管

## 验收結果
- 有一筆 `退款 991` 後續 `991 點？` 能命中 context
- 任務「Code / Refund / Promo」可成功生成 plan 並 Run All
- 共享記憶 timeline 可按 workspace 檢索
