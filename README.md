# BuyerOS Production Repository

BuyerOS 是一個多代理（multi‑agent）管理系統，目的是簡化線上商店的
營運和財務流程。這個 repository 提供一個可部署的後端 API、簡單的
命令行示範和測試，以及容器化部署配置。其核心特點包括：

* **持久記憶體：** 使用 Supabase/PostgreSQL 儲存訊息與狀態，沒有
  Supabase 時自動回退到本地記憶儲存。
* **分工代理：** 目前包含營運代理（OpsAgent）和財務代理
  （FinanceAgent）。代理能透過工具執行具體操作，例如退款或
  OCR（佔位）。
* **Supervisor 路由：** 根據關鍵字將訊息分配給相應代理，或在
  輸入純數字時查詢先前對話記憶。
* **Webhook API：** 透過 FastAPI 提供 `/telegram/webhook` 用於與
  Telegram Bot 整合，也提供 `/ping` 健康檢查。
* **Context Hub：** 提供 `/context/write`、`/context/search`、
  `/context/summarize`、`/context/session/{session_id}` 和 `/agents/run`，
  讓 Claude、Cursor、OpenAI、Gemini、DeepSeek、MiniMax、Grok、
  Perplexity、Hermes、OpenClaw 等 provider/client 共用同一套業務記憶。
* **API Key 保護：** 設定 `BUYEROS_API_KEY` 後，所有 context/agent API
  都需要 `X-Buyeros-Api-Key` 或 `Authorization: Bearer`。
* **Audit Trail：** context/agent API 操作會寫入 `["buyeros", "audit"]`
  namespace，方便部署後追蹤。
* **Readiness/Provider Status：** `/health/ready` 用於部署檢查，
  `/providers` 可查看 provider/model 設定狀態，provider 失敗時會按
  fallback chain 降級並寫入 context。
* **業務自動化：** 提供日報、OCR 入帳、對帳、異常告警、人工覆核與
  retry 狀態 API。
* **繁中管理 UI：** `frontend/` 提供 Next.js 管理台，可查 provider、
  session 記憶、重跑任務與執行業務自動化。
* **單元測試：** 使用 PyTest 驗證記憶儲存、代理行為與 Supervisor
  路由。

## 結構

```text
buyeros-production-repo/
├── backend/
│   ├── app/             # 核心代碼：agents、memory、tools、workflows
│   ├── tests/           # PyTest 測試
│   ├── scripts/         # 輔助腳本（預留）
│   ├── requirements.txt # Python 依賴
│   ├── Dockerfile       # 後端容器構建
│   ├── demo_cli.py      # 命令行示範
├── frontend/            # Next.js 繁中管理台
├── infra/               # 部署、smoke、backup、rollback 腳本
├── docs/                # 架構與部署資料
├── .github/workflows/   # CI 流程
├── docker-compose.yml   # 容器編排
├── .env.example         # 環境變數範本
├── AGENTS.md            # 代理與工具說明（預留）
└── README.md            # 本檔案
```

## 快速開始

1. **準備環境：** 安裝 Python 3.9+，複製 `.env.example` 為 `.env` 並設置
   `SUPABASE_URL`、`SUPABASE_KEY`、`TELEGRAM_BOT_TOKEN` 等環境變數。
2. **安裝依賴：**

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **啟動伺服器：**

   ```bash
   uvicorn app.workflows.main:create_app --factory --reload --host 0.0.0.0 --port 8000
   ```

4. **配置 Telegram Webhook：** 將您的 Telegram Bot token 填入 `.env`，
   然後使用 Telegram Bot API 設定 webhook，例如：

   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
     -d url=https://your-domain.com/telegram/webhook
   ```

5. **本地 CLI 測試：** 若沒有 Telegram，您可以直接執行命令行示範：

   ```bash
   python backend/demo_cli.py
   ```

6. **執行測試：**

   ```bash
   cd backend
   pytest -q
   ```

7. **啟動管理 UI：**

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   若你只有 `node` 沒有 `npm`，可改為：

   ```bash
   cd frontend
   node ./node_modules/next/dist/bin/next dev
   ```

## 容器化部署

本專案包含 `docker-compose.yml` 用於快速部署。請確保您安裝了
Docker 和 Docker Compose，然後：

```bash
cp .env.example .env
docker compose up --build
```

要只重啟前端而唔洗全部服務，可直接用：

```bash
bash infra/restart_frontend.sh
```

注意：唔好再喺指令後面亂加 `#` 註解。`#` 入到 shell 會變成獨立指令，出現 `command not found`。

API Key 快速測試（本機除錯）：

```bash
# 用同一條 key 打 API 時，可以加查詢參數直接測試
curl "http://127.0.0.1:3000/api/buyeros/health/ready?k=$BUYEROS_API_KEY"
```

前端頁面只要一次開咗含 `?k=<API_KEY>` 的網址，瀏覽器後續所有 `/api/buyeros/...` 請求都會帶同一組 key：

```text
http://127.0.0.1:3000/?k=$BUYEROS_API_KEY
```

此操作會建立 `backend` 與 `redis` 服務並啟動應用程式。如果您有
Supabase 資料庫憑證，容器會自動連線儲存長期記憶；Redis 用於短期
runtime/session 狀態。Compose 也會啟動 `frontend` 管理台。

## Context API Example

```bash
curl -X POST http://localhost:8000/context/write \
  -H "Content-Type: application/json" \
  -H "X-Buyeros-Api-Key: $BUYEROS_API_KEY" \
  -d '{"source_provider":"claude","session_id":"demo","task_id":"t1","content":{"text":"Refund 991 was handled"},"summary":"Refund 991 handled"}'

curl -X POST http://localhost:8000/context/search \
  -H "Content-Type: application/json" \
  -H "X-Buyeros-Api-Key: $BUYEROS_API_KEY" \
  -d '{"query":"991","session_id":"demo"}'
```

## Provider Routing

In v1, provider adapters are thin. If `OPENROUTER_API_KEY` is configured,
Claude/Gemini/DeepSeek/MiniMax/Grok/Perplexity/OpenAI-style provider calls
are routed through OpenRouter using the `OPENROUTER_MODEL_*` env vars. If the
key is missing, providers fail gracefully and still write task context.

## Production Checks

- `GET /ping`: simple liveness check.
- `GET /health/ready`: memory, Redis and provider readiness.
- `GET /providers`: provider/model status, protected by `BUYEROS_API_KEY`.
- `GET /audit/search`: recent audit events, protected by `BUYEROS_API_KEY`.
- `GET /projects`: three canonical lines (`buyer_ai`, `commerce`, `xau`).
- `POST /tasks/dispatch_plan`: create a deterministic subtask plan.
- `POST /tasks/{task_id}/run_all`: run subtasks until completed/blocked/max steps.
- `POST /memory/timeline`: inspect context, routing, run_all, audit and task history.
- `POST /automation/daily-report`: create report snapshot.
- `POST /automation/ocr-posting`: create OCR accounting entry.
- `POST /automation/reconcile`: compare totals and create mismatch alerts.

正式上線驗收：

```bash
python backend/scripts/validate_env.py --env .env.production.local
bash infra/smoke_api.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY"
bash infra/smoke_telegram_webhook.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" "$TELEGRAM_WEBHOOK_SECRET"
bash infra/smoke_24h.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY" 24 3600
```

One-command gate audit:

```bash
bash infra/go_live_audit.sh .env.production.local "$PUBLIC_BASE_URL" root@206.189.116.155 root@167.172.60.38
```

`smoke_api.sh` validates the core API and then runs the three-line smoke:
`buyer_ai` report/refund/OCR/reconciliation routing, `commerce` shop
order/inventory/support/finance data paths, `xau` promo/live metrics, and
BuyerOS dispatch/run_all/timeline. To run only the core API checks:

```bash
BUYEROS_SKIP_THREE_SYSTEMS_SMOKE=1 bash infra/smoke_api.sh "$PUBLIC_BASE_URL" "$BUYEROS_API_KEY"
```

`smoke_telegram_webhook.sh` posts Telegram-shaped webhook updates directly to
BuyerOS and verifies the shared context/session state. Real Telegram webhook
activation still requires an HTTPS domain and `infra/set_telegram_webhook.sh`.
For the primary VPS, `BUYEROS_DOMAIN=buyeros.206.189.116.155.sslip.io` can be
used as a temporary HTTPS domain until a purchased domain is ready.

For staging only, if `sslip.io` certificate issuance is rate limited, smoke can
use:

```bash
BUYEROS_CURL_INSECURE=1 bash infra/smoke_api.sh "https://buyeros.167.172.60.38.sslip.io" "$BUYEROS_API_KEY"
bash infra/smoke_api.sh "http://167.172.60.38:8000" "$BUYEROS_API_KEY"
```

Do not use `BUYEROS_CURL_INSECURE=1` for production acceptance.

三個 Workspace 上線順序請見：

```text
docs/THREE_WORKSPACE_GO_LIVE_PLAN.md
```

## Production Inputs

Use [.env.production.template](.env.production.template) and
[docs/PRODUCTION_INPUTS.md](docs/PRODUCTION_INPUTS.md) to fill the missing VPS,
domain, Supabase, Telegram and OpenRouter values before deployment.

## 下一步

此版本為基礎框架，提供完整的骨架和測試。後續可以根據業務需求
擴充代理、工具和前端介面，例如：

* **連結真實支付接口** 處理退款
* **整合 OCR 服務** 提取收據文字
* **接入真實排程器** 定時推送日報和異常告警
* **把管理 UI 接到正式登入/權限系統**

歡迎貢獻或提出改進建議！
