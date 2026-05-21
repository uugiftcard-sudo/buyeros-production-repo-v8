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
  `/providers` 可查看 provider/model 設定狀態。
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
├── frontend/            # Telegram Mini App 前端（佔位）
├── infra/               # 基礎建設配置（預留）
├── docs/                # 進一步文檔（預留）
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

## 容器化部署

本專案包含 `docker-compose.yml` 用於快速部署。請確保您安裝了
Docker 和 Docker Compose，然後：

```bash
cp .env.example .env
docker compose up --build
```

此操作會建立 `backend` 與 `redis` 服務並啟動應用程式。如果您有
Supabase 資料庫憑證，容器會自動連線儲存長期記憶；Redis 用於短期
runtime/session 狀態。

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

## Production Inputs

Use [.env.production.template](.env.production.template) and
[docs/PRODUCTION_INPUTS.md](docs/PRODUCTION_INPUTS.md) to fill the missing VPS,
domain, Supabase, Telegram and OpenRouter values before deployment.

## 下一步

此版本為基礎框架，提供完整的骨架和測試。後續可以根據業務需求
擴充代理、工具和前端介面，例如：

* **連結真實支付接口** 處理退款
* **整合 OCR 服務** 提取收據文字
* **新增報表或警報代理** 提供即時分析
* **開發 Telegram Mini App 前端** 改善使用者體驗

歡迎貢獻或提出改進建議！
