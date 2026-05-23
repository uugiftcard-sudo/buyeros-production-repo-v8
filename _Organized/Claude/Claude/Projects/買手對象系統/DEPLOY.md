# BuyerOS — 本地部署指南
> 日期：2026-05-23

---

## 前置要求

- Node.js ≥ 18
- Deno ≥ 1.40（用於 Edge Functions）
- [Supabase CLI](https://supabase.com/docs/guides/cli)
- [Telegram Bot Token](https://core.telegram.org/bots#creating-bot-your-first-bot)

---

## Step 1：環境設定

```bash
# 複製環境變量模板
cp .env.example .env.local

# 編輯 .env.local，填入以下值：
# SUPABASE_URL=https://<project-ref>.supabase.co
# SUPABASE_SERVICE_ROLE_KEY=<from Supabase Dashboard>
# TELEGRAM_BOT_TOKEN=<from BotFather>
# ADMIN_TG_ID=<your Telegram user ID>
```

---

## Step 2：連結 Supabase Project

```bash
npx supabase login
npx supabase link --project-ref jnzdklfjdjmhjrhntljp
```

---

## Step 3：部署 Database Schema

### 方式 A：CLI（推薦）

```bash
# 按順序執行所有 migration
npx supabase db push --file supabase/migrations/0001_initial_reconstructed.sql
npx supabase db push --file supabase/migrations/0002_accounting_layer.sql
npx supabase db push --file supabase/migrations/0002b_config_driven_posting.sql
npx supabase db push --file supabase/migrations/0003_rls_and_audit.sql
```

### 方式 B：Supabase Studio

1. 開啟 https://supabase.com/dashboard/project/jnzdklfjdjmhjrhntljp
2. 左側 SQL Editor → New Query
3. 逐一貼上並執行 migration files

---

## Step 4：載入測試數據（開發環境）

```bash
# 在 Supabase Studio SQL Editor
\i supabase/seed.sql

# 驗證
SELECT COUNT(*) FROM buyers;   -- 應為 3
SELECT COUNT(*) FROM customers; -- 應為 3
SELECT COUNT(*) FROM orders;   -- 應為 4
```

---

## Step 5：部署 Edge Functions

```bash
cd supabase

# 部署所有 functions
npx supabase functions deploy customers
npx supabase functions deploy orders
npx supabase functions deploy transactions
npx supabase functions deploy refunds
npx supabase functions deploy dashboard
npx supabase functions deploy telegram-webhook

# 設定 Edge Function secrets
supabase secrets set BOT_API_KEY=<your-bot-api-key>
supabase secrets set TELEGRAM_BOT_TOKEN=<your-telegram-token>
supabase secrets set ADMIN_TG_ID=<your-telegram-id>
```

### 本地測試 Edge Functions

```bash
# 啟動本地 functions 服務器
npx supabase functions serve --env-file .env.local

# 測試 customers API
curl -X GET "http://localhost:54321/functions/v1/customers" \
  -H "Authorization: Bearer <ANON_KEY>" \
  -H "apikey: <ANON_KEY>"
```

---

## Step 6：設定 Telegram Webhook

```bash
# 替換 <BOT_TOKEN> 和 <PROJECT_REF>
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"https://jnzdklfjdjmhjrhntljp.supabase.co/functions/v1/telegram-webhook\"}"
```

### 驗證 Webhook

```bash
# 查看 webhook 狀態
curl "https://api.telegram.org/bot<BOT_TOKEN>/getWebhookInfo"

# 刪除 webhook（如需）
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/deleteWebhook"
```

### 測試 Bot

1. 在 Telegram 搜索你的 bot
2. 發送 `/start`
3. 確認收到歡迎消息
4. 發送 `/myorders` 確認返回訂單列表

---

## Step 7：啟動 Admin Web UI

```bash
cd apps/admin
npm install

# 複製環境變量
cp ../../.env.example ../../.env.local
# 編輯 .env.local，填入：
# NEXT_PUBLIC_SUPABASE_URL=https://jnzdklfjdjmhjrhntljp.supabase.co
# NEXT_PUBLIC_SUPABASE_ANON_KEY=<from Supabase Dashboard>

npm run dev
# 開啟 http://localhost:3000
```

---

## Step 8：驗證部署

### API 健康檢查

```bash
# Dashboard summary
curl "https://jnzdklfjdjmhjrhntljp.supabase.co/functions/v1/dashboard/summary" \
  -H "Authorization: Bearer <ANON_KEY>" \
  -H "apikey: <ANON_KEY>"

# Telegram webhook
curl "https://jnzdklfjdjmhjrhntljp.supabase.co/functions/v1/telegram-webhook"
```

### RLS 驗證

在 Supabase Studio SQL Editor 執行：

```sql
-- 檢查 RLS 狀態
SELECT * FROM recon_rls_audit();

-- 測試 audit_log 不可篡改
UPDATE audit_log SET reason = 'test' WHERE id = (SELECT id FROM audit_log LIMIT 1);
-- 應該失敗：audit_log is append-only
```

---

## 常見問題

### Edge Function 部署失敗

```
Error: Function name must be lowercase alphanumeric
```
→ 確保 function folder 名稱是小寫字母（如 `customers/` 而非 `Customers/`）

### Telegram Webhook 無法接收消息

→ 確認 `TELEGRAM_BOT_TOKEN` 已在 Supabase secrets 中設定
→ 確認 webhook URL 是 `https://`（不是 `http://`）

### Admin UI 無法連接 Supabase

→ 確認 `.env.local` 中 `NEXT_PUBLIC_SUPABASE_URL` 和 `NEXT_PUBLIC_SUPABASE_ANON_KEY` 正確
→ 確認在 Supabase Dashboard → Settings → API 中複製正確的 keys

### Migration 執行失敗

→ 確認 `0001` 先執行，再執行 `0002`、`0003`
→ 如有錯誤，用 Supabase Studio 單獨執行每條語句
