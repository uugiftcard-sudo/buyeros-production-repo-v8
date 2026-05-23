# BuyerOS（買手對象系統）

> 代購 / 採購中介平台的完整後端系統

[![Status](https://img.shields.io/badge/status-active-brightgreen.svg)](#)
[![Supabase](https://img.shields.io/badge/Supabase-PostgreSQL-orange.svg)](#)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](#)

---

## 📁 專案結構

```
買手對象系統/
├── ARCHITECTURE.md                    ← 系統架構文檔
├── GAP-REPORT.md                     ← Gap 分析報告（已完成）
│
├── .env.example                      ← 環境變量模板
├── .gitignore
│
├── supabase/
│   ├── migrations/
│   │   ├── 0001_initial_reconstructed.sql  ← 核心業務層 Schema（Tier 1-3）
│   │   ├── 0002_accounting_layer.sql      ← 會計層 Schema（Tier 4）✅
│   │   ├── 0002b_config_driven_posting.sql ← 配置驅動的 journal posting
│   │   └── 0003_rls_and_audit.sql         ← RLS + Audit Log ✅
│   │
│   ├── seed.sql                      ← 測試數據（3 買手 / 3 客戶 / 4 訂單）
│   │
│   └── functions/                    ← Supabase Edge Functions
│       ├── _shared/index.ts          ← 通用工具（統一錯誤、驗證、產生號）
│       ├── customers/index.ts         ← 客戶管理 API
│       ├── orders/index.ts           ← 訂單管理 API
│       ├── transactions/index.ts      ← 交易管理 API
│       ├── refunds/index.ts          ← 退款管理 API
│       ├── dashboard/index.ts        ← 儀表板 API
│       └── telegram-webhook/index.ts  ← Telegram Bot Webhook
│
├── apps/
│   └── admin/                        ← Admin Web UI（Next.js 14 App Router）
│       ├── package.json
│       ├── next.config.js
│       ├── tsconfig.json
│       ├── lib/
│       │   ├── supabase.ts          ← Supabase client
│       │   └── api.ts               ← Edge Functions API client
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── globals.css
│       │   ├── page.tsx             ← 儀表板
│       │   ├── orders/page.tsx       ← 訂單管理
│       │   ├── customers/page.tsx     ← 客戶管理
│       │   └── financials/page.tsx    ← 財務報表
│       └── components/
│           └── Sidebar.tsx
│
├── recon/
│   ├── supabase-audit.sql            ← 在 Supabase Studio 執行的 audit SQL
│   ├── check-enums.sql               ← 確認 enum 值的 SQL
│   └── vps-recon.sh                 ← VPS Recon 腳本
│
└── backup-system/                    ← 每日備份系統 ✅ 已完成
    ├── README.md
    ├── SECRETS-CHECKLIST.md
    └── scripts/
```

---

## ⚠️ Status: Schema 需要驗證

本專案的核心 schema 係從備份文件推斷重建（`supabase/migrations/0001_initial_reconstructed.sql`）。
**未經過真實 Supabase DB 驗證。**

### 立即需要做的事

1. **驗證 Schema**：在 Supabase Studio SQL Editor 執行 `recon/supabase-audit.sql`
2. **替換為真實 Schema**：
   ```bash
   npx supabase login
   npx supabase link --project-ref jnzdklfjdjmhjrhntljp
   npx supabase db dump --schema public > supabase/migrations/0001_initial.sql
   ```
3. **確認 Auth 方式**：Supabase Auth 或 Telegram OAuth？

---

## 🏗️ Tech Stack

| Component | 技術 | 狀態 |
|-----------|------|------|
| Primary DB | Supabase PostgreSQL | ✅ |
| Auth | ⚠️ 未確認 | 待確認 |
| 主要介面 | Telegram Bot | ✅ |
| 檔案儲存 | Supabase Storage (documents) | ✅ |
| 備份儲存 | Cloudflare R2 (buyeros-backups) | ✅ |
| VPS | DigitalOcean @ 206.189.116.155 | ✅ |
| API | Supabase Edge Functions (Deno) | ✅ 新增 |
| Admin UI | Next.js 14 App Router | ✅ 新增 |
| 會計層 | 複式記賬 + Journal Entries | ✅ |

---

## 🚀 快速開始

### 1. 克隆專案

```bash
git clone <repo-url>
cd 買手對象系統
```

### 2. 設定環境變量

```bash
cp .env.example .env.local
# 填入實際值（見 .env.example）
```

### 3. 連結 Supabase

```bash
npx supabase login
npx supabase link --project-ref jnzdklfjdjmhjrhntljp
```

### 4. 部署 Database Schema

```bash
# 按順序執行 migration
npx supabase db push --file supabase/migrations/0001_initial_reconstructed.sql
npx supabase db push --file supabase/migrations/0002_accounting_layer.sql
npx supabase db push --file supabase/migrations/0002b_config_driven_posting.sql
npx supabase db push --file supabase/migrations/0003_rls_and_audit.sql
```

或在 Supabase Studio SQL Editor 逐一貼上執行。

### 5. 載入測試數據（開發環境）

```sql
-- 在 Supabase Studio SQL Editor 執行
\i supabase/seed.sql
```

### 6. 部署 Edge Functions

```bash
cd supabase
npx supabase functions deploy customers
npx supabase functions deploy orders
npx supabase functions deploy transactions
npx supabase functions deploy refunds
npx supabase functions deploy dashboard
npx supabase functions deploy telegram-webhook
```

### 7. 啟動 Admin Web UI

```bash
cd apps/admin
npm install
npm run dev
# 開啟 http://localhost:3000
```

### 8. 設定 Telegram Webhook

```bash
# 替換 <BOT_TOKEN> 和 <YOUR_SUPABASE_URL>
curl -X POST "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://<project-ref>.supabase.co/functions/v1/telegram-webhook"}'
```

---

## 🌐 API 端點

### Edge Functions REST API

所有 API 均以 `/functions/v1/` 為前綴，需要 `Authorization: Bearer <ANON_KEY>` header。

#### 客戶管理

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/functions/v1/customers` | 客戶列表（支援分頁、搜索） |
| POST | `/functions/v1/customers` | 新增客戶 |
| GET | `/functions/v1/customers/:id` | 取得單一客戶 |
| PATCH | `/functions/v1/customers/:id` | 更新客戶 |
| DELETE | `/functions/v1/customers/:id` | 軟刪除客戶 |

#### 訂單管理

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/functions/v1/orders` | 訂單列表 |
| GET | `/functions/v1/orders/stats` | 訂單統計 |
| POST | `/functions/v1/orders` | 建立新訂單 |
| GET | `/functions/v1/orders/:id` | 取得訂單（含明細） |
| PATCH | `/functions/v1/orders/:id` | 更新訂單狀態 |
| PATCH | `/functions/v1/orders/:id/assign` | 分配買手 |
| DELETE | `/functions/v1/orders/:id` | 取消訂單 |

#### 交易管理

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/functions/v1/transactions` | 交易列表 |
| POST | `/functions/v1/transactions` | 記錄收款 |
| GET | `/functions/v1/transactions/:id` | 取得交易 |
| PATCH | `/functions/v1/transactions/:id` | 更新交易狀態 |

#### 退款管理

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/functions/v1/refunds` | 退款列表 |
| POST | `/functions/v1/refunds` | 申請退款 |
| GET | `/functions/v1/refunds/:id` | 退款詳情 |
| PATCH | `/functions/v1/refunds/:id` | 更新退款狀態 |

#### 儀表板

| Method | Endpoint | 說明 |
|--------|----------|------|
| GET | `/functions/v1/dashboard/summary` | 總覽數據 |
| GET | `/functions/v1/dashboard/buyers` | 買手列表 |
| GET | `/functions/v1/dashboard/financials` | 財務報表 |

#### Telegram Webhook

| Method | Endpoint | 說明 |
|--------|----------|------|
| POST | `/functions/v1/telegram-webhook` | Telegram 更新接收 |
| GET | `/functions/v1/telegram-webhook` | 健康檢查 |

---

## 📊 Database Schema

### Migration 執行順序

```
0001_initial_reconstructed.sql  → 核心業務層（buyers/customers/orders/transactions/refunds/settlements）
0002_accounting_layer.sql        → 會計層（accounts/journal_entries/journal_lines/accounting_periods）
0002b_config_driven_posting.sql  → 配置驅動的 journal posting
0003_rls_and_audit.sql           → RLS policies + audit_log
```

### 主要表結構

| Table | 說明 | Tier |
|-------|------|------|
| `buyers` | 買手主表 | 1 |
| `customers` | 客戶主表 | 1 |
| `orders` | 訂單主表 | 2 |
| `order_items` | 訂單明細 | 2 |
| `transactions` | 收款記錄 | 3 |
| `refunds` | 退款記錄 | 3 |
| `settlements` | 買手結算 | 3 |
| `accounts` | 會計科目表 | 4 |
| `journal_entries` | 日記帳 | 4 |
| `journal_lines` | 分錄行 | 4 |
| `accounting_periods` | 會計期間 | 4 |
| `invoices` | 發票 | 5 |
| `documents` | 文件存儲記錄 | 5 |
| `audit_log` | 審計日誌 | 6 |

---

## 🤖 Telegram Bot 命令

### 買手指令

```
/start              — 開啟 bot，綁定 telegram_user_id
/myorders           — 查看我的訂單
/balance            — 查看結算餘額
/neworder           — 新下單
/help               — 幫助
```

### 管理員指令（需 ADMIN_TG_ID）

```
/admin_orders       — 所有訂單管理
/admin_buyers      — 買手管理
/admin_refunds     — 退款審批
/broadcast         — 群發通知
```

---

## 📈 會計報表

套用 `0002_accounting_layer.sql` 後可使用以下 SQL 視圖：

```sql
-- 試算表
SELECT * FROM v_trial_balance;

-- 月度損益
SELECT * FROM v_monthly_pnl ORDER BY period DESC;

-- P&L 摘要
SELECT * FROM v_pnl_summary ORDER BY period DESC, sort_order;

-- 資產負債表（截至某日）
SELECT * FROM v_balance_sheet('2026-05-31');

-- 應收帳齡
SELECT * FROM v_ar_aging;

-- 月結（鎖定期間）
SELECT close_accounting_period('2026-05');
```

---

## 🔐 Secrets

見 `backup-system/SECRETS-CHECKLIST.md` 的完整 vault structure。
所有 secrets 存於 Bitwarden / 1Password，**永遠不要 commit 到 git**。

---

## 🔧 本地開發

### Edge Functions 本地調試

```bash
npx supabase functions serve customers --env-file .env.local
```

### Admin UI 本地開發

```bash
cd apps/admin
npm install
npm run dev
```

### 驗證 Enum 值（部署前必做）

在 Supabase Studio 執行 `recon/check-enums.sql`，確保以下值與 migration 匹配：

- `transactions.type`：payment, deposit, balance, commission
- `refunds.status`：pending, approved, processing, completed, rejected

---

## 📋 Priority 行動計劃

| Priority | 任務 | 狀態 |
|---------|------|------|
| **P1** | Schema + Code 入 Git | ✅ 完成 |
| **P2** | 會計層 Schema 設計 | ✅ 完成（需驗證）|
| P3 | RLS + Audit Log 確認 | ✅ 完成（需執行）|
| P4 | Edge Functions 部署驗證 | ⏳ 待做 |
| P5 | Telegram Webhook 對接 | ⏳ 待做 |
| P6 | Admin Web UI 完善 | ⏳ 待做 |
| P7 | 歷史數據 Backfill Journal Entries | ⏳ 待做 |

---

## 📦 部署

### Supabase Edge Functions

```bash
# 部署所有 functions
cd supabase
for fn in customers orders transactions refunds dashboard telegram-webhook; do
  npx supabase functions deploy $fn
done
```

### Admin UI（Vercel）

```bash
cd apps/admin
vercel deploy
# 或本地
npm run build && npm start
```

---

*最後更新：2026-05-23*
