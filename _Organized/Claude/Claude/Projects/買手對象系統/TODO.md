# BuyerOS — TODO / 待完成功能清單

> 更新日期：2026-05-23
> 負責人：AI Agent 3（買手對象系統開發）

---

## 🔴 P1 — 立即行動（影響業務）

### P1.1 驗證真實 Schema

- [ ] **在 Supabase Studio 執行 `recon/supabase-audit.sql`**
- [ ] **下載 12 個 result CSV，確認 24 張表的結構**
- [ ] **執行 `recon/check-enums.sql`**，確認 `transactions.type` 和 `refunds.status` 的實際值
- [ ] 將 `supabase/migrations/0001_initial_reconstructed.sql` 替換為真實 schema dump：

```bash
npx supabase login
npx supabase link --project-ref jnzdklfjdjmhjrhntljp
npx supabase db dump --schema public > supabase/migrations/0001_actual_verified.sql
```

### P1.2 確認 Auth 方式

- [ ] 確認用 Supabase Auth 還是 Telegram OAuth
- [ ] 如果用 Supabase Auth：在 `buyers` / `customers` 表加 `auth_user_id UUID REFERENCES auth.users(id)`
- [ ] 更新 `0003_rls_and_audit.sql` 的 RLS policy 以使用正確的 auth 方式

### P1.3 部署 Migration

- [ ] 在 Supabase Studio 按順序執行 4 個 migration
- [ ] 驗證所有 table 被正確建立
- [ ] 執行 `SELECT * FROM recon_rls_audit();` 確認 RLS 狀態

---

## 🟡 P2 — 高優先（核心功能）

### P2.1 Edge Functions 部署驗證

- [ ] 部署 `customers` function：`npx supabase functions deploy customers`
- [ ] 部署 `orders` function：`npx supabase functions deploy orders`
- [ ] 部署 `transactions` function：`npx supabase functions deploy transactions`
- [ ] 部署 `refunds` function：`npx supabase functions deploy refunds`
- [ ] 部署 `dashboard` function：`npx supabase functions deploy dashboard`
- [ ] 部署 `telegram-webhook` function
- [ ] **驗證每個 API endpoint**：使用 Postman / curl 測試 CRUD 操作
- [ ] 替換 Hardcoded 內容：
  - [ ] `supabase/functions/telegram-webhook/index.ts` 的 `ADMIN_TG_ID`
  - [ ] `supabase/functions/_shared/index.ts` 的 `BOT_API_KEY` env var

### P2.2 Telegram Bot 對接

- [ ] 在 `BotFather` 設定 Webhook URL
- [ ] 驗證 `/start` 命令正確創建客戶記錄
- [ ] 驗證 `/myorders` 返回正確訂單
- [ ] 驗證 `callback_query`（inline keyboard）正確處理
- [ ] 設定 `TELEGRAM_BOT_TOKEN` 在 Supabase Edge Functions secrets

### P2.3 Admin Web UI

- [ ] 完成 `apps/admin` 的 `npm install` + `npm run dev`
- [ ] **新增頁面**：
  - [ ] `app/orders/[id]/page.tsx` — 訂單詳情（含 items、transactions）
  - [ ] `app/orders/new/page.tsx` — 新建訂單表單
  - [ ] `app/buyers/page.tsx` — 買手管理頁面
  - [ ] `app/transactions/page.tsx` — 交易記錄頁面
  - [ ] `app/refunds/page.tsx` — 退款管理頁面
  - [ ] `app/periods/page.tsx` — 月結管理頁面
- [ ] **新增功能**：
  - [ ] 新建訂單時的 buyer assignment UI
  - [ ] 退款審批 UI（approve/reject/processing/completed）
  - [ ] 買手結算管理（查看、審批結算單）
  - [ ] 客戶新建表單
- [ ] **完善 financials 頁面**：
  - [ ] 圖表化顯示 P&L（月度趨勢）
  - [ ] 圖表化顯示 Trial Balance
  - [ ] 圖表化顯示收入/支出分布

---

## 🟢 P3 — 中優先（功能完善）

### P3.1 歷史數據 Backfill

- [ ] 執行 `journal_posting_rules` seed 確認
- [ ] 執行 backfill 歷史 journal entries：

```sql
SELECT * FROM backfill_journal_entries();
```

- [ ] 驗證 `v_trial_balance` 有數據
- [ ] 驗證 `v_monthly_pnl` 有數據

### P3.2 Seed Data 完善

- [ ] 在 `.env.local` 加入 `BOT_API_KEY`
- [ ] 驗證 seed data 的 FK 關係正確
- [ ] 確認 buyer_documents table（如存在）的 seed

### P3.3 通訊記錄系統

- [ ] 設計 `communications` table：
  ```sql
  CREATE TABLE communications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    customer_id UUID REFERENCES customers(id),
    buyer_id UUID REFERENCES buyers(id),
    channel TEXT CHECK (channel IN ('telegram', 'whatsapp', 'email', 'phone', 'sms')),
    direction TEXT CHECK (direction IN ('inbound', 'outbound')),
    subject TEXT,
    content TEXT,
    attachments TEXT[],  -- storage paths
    tags TEXT[],         -- 'order-inquiry', 'complaint', 'followup'
    created_by UUID,
    is_archived BOOLEAN DEFAULT FALSE
  );
  ```

- [ ] Edge Function：`POST /functions/v1/communications`
- [ ] Admin UI：`app/communications/page.tsx`

### P3.4 買手 KYC 管理

- [ ] 確認 `buyer_documents` table 是否存在
- [ ] 新增 KYC 審批 UI：
  - [ ] 查看 KYC 文件（從 Supabase Storage）
  - [ ] approve/reject KYC
  - [ ] KYC 到期提醒（未來：pg_cron job）

---

## 🔵 P4 — 低優先（Nice-to-have）

### P4.1 通知系統

- [ ] Email fallback（nodemailer / Resend）
- [ ] 買手新訂單 Telegram 通知
- [ ] 退款狀態變更通知
- [ ] 結算完成通知

### P4.2 訂單狀態機完善

- [ ] 狀態變更時的業務邏輯驗證：
  - [ ] `pending → assigned`：需指定 buyer
  - [ ] `in_procurement → received`：需提交收據文件
  - [ ] `delivered → completed`：需已收全款（balance_due = 0）
- [ ] 加入 Edge Function 層面的狀態機驗證

### P4.3 買手評分系統

- [ ] 設計 `ratings` table
- [ ] 交易完成後邀請客戶評分
- [ ] Buyer ranking by rating

### P4.4 文檔上傳（收據管理）

- [ ] Supabase Storage 上傳 API
- [ ] 收據上傳 UI（在訂單詳情頁）
- [ ] 發票 PDF 生成（`invoices.pdf_storage_path`）

### P4.5 匯出功能

- [ ] Edge Function：`GET /functions/v1/export/transactions?period=2026-05`
- [ ] 輸出 CSV 格式
- [ ] 輸出 PDF 月結報告

### P4.6 測試覆蓋

- [ ] 為 Edge Functions 編寫 Deno 測試
- [ ] 為 Admin UI 編寫 Playwright E2E 測試
- [ ] 測試關鍵路徑：新建訂單 → 分配買手 → 提交收據 → 收貨 → 收款 → 完成

---

## ⚠️ 已知問題

| 問題 | 嚴重度 | 狀態 | 解決方案 |
|------|--------|------|----------|
| Enum 值未驗證 | 🔴 高 | ⏳ 待確認 | 執行 `recon/check-enums.sql` |
| RLS policy placeholder | 🟡 中 | ⏳ 待實現 | 確認 auth 方式後更新 |
| 會計層未被真實 DB 驗證 | 🟡 中 | ⏳ 待部署 | 部署後驗證視圖 |
| Telegram Webhook URL 未設定 | 🟡 中 | ⏳ 待設定 | BotFather setWebhook |

---

## 🎯 成功標準

- [ ] 所有 4 個 migration 在真實 Supabase 執行成功
- [ ] Edge Functions API 所有端點可用（返回正確 JSON）
- [ ] Telegram Bot 可以接收消息並創建訂單
- [ ] Admin UI 儀表板顯示正確數據
- [ ] RLS policy 正確阻止未授權訪問
- [ ] `v_trial_balance` 和 `v_monthly_pnl` 有正確數據
