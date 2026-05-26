# 三線功能補齊計劃：buyer_ai / commerce / xau
## Summary
按「三線全部」補齊，分三批做。第一批補 `buyer_ai` 買手底座；第二批補 `commerce` 真網店營運流；第三批補 `xau` campaign/metrics。退款對帳、退款比對、OCR 入帳、manual review 主責歸 `buyer_ai`，`commerce` 只提供網店訂單、售後、支付、庫存、客服資料作為比對來源。

## 第一批：buyer_ai 買手底座
- 修正文檔邊界：`buyer_ai` 代表 BuyerOS / AI 中樞 / Context Hub / Telegram / 買手 Report / 採購 ROI / 退款 / OCR / 對帳 / reconciliation / manual review
- 補齊 smoke 驗收：`/projects`、`/tasks/dispatch_plan`、`/tasks/{id}/run_all`、`/memory/timeline`、Telegram mock、ops status
- 更新受影響文檔：`GO_LIVE_EVIDENCE.md`、`PHASE2_CURRENT_STATE.md`、`THREE_WORKSPACE_GO_LIVE_PLAN.md`、`PHASE2_HANDOFF_FOR_CURSOR.md`、`SHOPS_SETUP.md`、`infra/README.md`

## 第二批：commerce 網店自動系統
- 補齊第一條真營運鏈：order / after-sales / payment / inventory / support → 提供資料給 `buyer_ai` refund/OCR/reconciliation → report/timeline
- 明確 `commerce` 負責：訂單、庫存、客服、網店收支、Shopify/TikTok/Custom API、AI live selling
- 明確 `commerce` 不主責：退款對帳、退款比對、OCR 入帳、manual review
- 檢查 CLOTH 現有 API：finance/inventory/support/wishlist/mobile nav

## 第三批：xau 系統
- 驗證 XAU `server/routes/wechat.js` crash fix 已穩定
- 補 campaign/conversion/metrics 最小閉環
- 保持 XAU 獨立，任務狀態回寫 BuyerOS memory/timeline

## Test Plan
- BuyerOS：`pytest + smoke_api.sh`
- Commerce：`npm run lint && npm run check && npm test`
- XAU：`npm test && npm run test:server`

## Acceptance Criteria
- Docs 裡再無「退款/OCR/對帳屬 commerce 或 BuyerOS 共用能力」文案
- Docs 明確寫出「退款/OCR/對帳/reconciliation/manual review 屬 `buyer_ai`」
- Docs 明確寫出「`commerce` 只提供網店資料來源」
- `/projects` 只返回 canonical 三線：`buyer_ai / commerce / xau`
- `buyer_ai` automation 能跑退款/OCR/對帳 smoke
- CLOTH commerce API 前端 build/lint/test 通過
- XAU server/root tests 通過
- 不提交 secrets、不改 production env、不做 dirty deploy
