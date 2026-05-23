# BuyerOS（買手對象系統）— 系統架構文檔

> 版本：1.1.0
> 生成：2026-05-23
> 狀態：P2 會計層已完成 ⚠️ 待驗證真實 schema

---

## 1. 業務模型（Business Model）

### 1.1 角色（Actors）

| 角色 | 說明 | 主要操作 |
|------|------|----------|
| **Admin** | 平台管理員 | 全部操作、結算審批、KYC 審批 |
| **Buyer（買手）** | 實體採購者 | 接單、提交收據、查看結算 |
| **Customer（客戶）** | 下單採購的人 | 下單、付款、查看進度、退款 |
| **System** | 自動化程序 | 發送通知、生成 journal entry |

### 1.2 核心業務流程

```
[客戶] 下單 → 平台分配買手 → [買手] 採購 → 收貨入庫
    → 客戶付款（deposit/balance）→ 交付 → 完成結算
    ↘ 退貨/退款流程
```

### 1.3 關鍵數字（估算）

| 指標 | 估算 |
|------|------|
| 日成交單數 | ~10-50 單 |
| 月 GMV | HK$500K+ |
| 買手人數 | ~5-20 人 |
| Table 數量 | ~24 張（已確認） |
| 日資料中斷成本 | HK$500K（見 backup-system README） |

---

## 2. 技術架構（Tech Stack）

### 2.1 核心組件

```
┌─────────────────────────────────────────────────────┐
│                   Client Layer                        │
│  Telegram Bot (主要介面)  ←── 買手 + 客戶 + Admin     │
│  Admin Web UI (未確認)                                │
└────────────────────────┬──────────────────────────────┘
                         │ Bot Commands / Web API
┌────────────────────────▼──────────────────────────────┐
│                   Backend Layer                        │
│  Telegram Bot Server (Node/Deno?)                     │
│  Supabase Edge Functions (?)                          │
└────────────────────────┬──────────────────────────────┘
                         │
┌────────────────────────▼──────────────────────────────┐
│                   Data Layer                           │
│  Supabase PostgreSQL (primary DB)                     │
│    ↳ 24 tables, RLS enabled (?)                     │
│  Supabase Storage (documents bucket)                  │
│    ↳ 收據 / 發票 / KYC 文件                          │
│  Supabase Auth (?)                                    │
└──────────────────────────────────────────────────────┘
                         │
┌────────────────────────▼──────────────────────────────┐
│                   Infrastructure                      │
│  VPS: DigitalOcean @ 206.189.116.155                  │
│  Backup: Cloudflare R2 (buyeros-backups bucket)       │
│  GitHub: buyeros-backups repo                         │
└──────────────────────────────────────────────────────┘
```

### 2.2 Stack 清單

| Component | Technology | Status |
|-----------|-----------|--------|
| Primary Database | Supabase PostgreSQL | ✅ 已知使用 |
| Auth | Supabase Auth 或 Telegram OAuth | ⚠️ 未確認 |
| Primary Interface | Telegram Bot | ✅ 確認 |
| File Storage | Supabase Storage (documents bucket) | ✅ 確認 |
| Backup Storage | Cloudflare R2 | ✅ 確認 |
| VPS | DigitalOcean | ✅ 確認 |
| CI/CD | GitHub Actions | ✅ backup-system 使用中 |
| Secret Vault | Bitwarden / 1Password | ✅ SECRETS-CHECKLIST.md |
| Server Runtime | Node.js / Deno / Python | ⚠️ 未確認 |

---

## 3. 數據模型（Data Model）

> ⚠️ 以下係根據業務邏輯重建的推斷 schema。
> 請用 `supabase/migrations/0001_initial_reconstructed.sql` 作為完整 SQL 藍本。
> 最終替換：`npx supabase db dump --schema public`

### 3.1 Entity-Relationship Overview

```
users (Supabase Auth)
    ↓ (via telegram_user_id)
buyers ←─────────────────── orders (assigned_buyer_id)
    ↓                           ↓
buyer_documents            order_items
                            ↓
customers ──────────────── orders (customer_id)
    ↓                           ↓
transactions ──────────── refunds ←──── settlements
    ↓                               (via buyer_id)
invoices
    ↓
journal_entries → journal_lines ← accounts
                                    ↑
                          accounting_periods
    ↓
documents (Supabase Storage)
```

### 3.2 Table 層級

| Tier | Tables | Confidence | Description |
|------|--------|-----------|-------------|
| **Tier 1** | buyers, customers | 高 | 核心實體 |
| **Tier 2** | orders, order_items | 高 | 業務流程 |
| **Tier 3** | transactions, refunds, settlements | 高 | 財務記錄 |
| **Tier 4** | accounts, journal_entries, journal_lines, accounting_periods | 中 | 會計層（⚠️ 可能未實現） |
| **Tier 5** | documents, invoices | 中 | 文檔 |
| **Tier 6** | audit_log | 低 | 審計（⚠️ 強烈建議新增） |

---

## 4. Bot Commands（推测）

> ⚠️ 未確認，以下係根據業務推斷的 Command 列表。
> 需用戶在 Telegram BotFather 截圖確認。

### 4.1 買手命令（Buyer Commands）
```
/start              — 開啟 bot，綁定 telegram_user_id
/myorders           — 查看我的訂單
/accept <order_id>  — 接單
/submit_receipt     — 提交收據（圖片）
/balance            — 查看結算餘額
/settings           — 修改個人資料
```

### 4.2 客戶命令（Customer Commands）
```
/start              — 開啟 bot
/neworder           — 新下單
/myorders          — 查看我的訂單
/pay <order_id>    — 付款
/track <order_id>   — 追蹤進度
/Refund <order_id>  — 申請退款
```

### 4.3 Admin 命令
```
/admin_orders       — 所有訂單管理
/admin_buyers      — 買手管理
/admin_refunds     — 退款審批
/admin_settlements  — 結算管理
/broadcast         — 群發通知
/backup_status     — 查看 backup 狀態
```

---

## 5. API / Edge Functions（推測）

> ⚠️ 未確認，以下係推斷的 endpoint。

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/functions/v1/create-order` | POST | 創建訂單 |
| `/functions/v1/assign-buyer` | POST | 分配買手 |
| `/functions/v1/record-payment` | POST | 記錄付款 |
| `/functions/v1/request-refund` | POST | 申請退款 |
| `/functions/v1/generate-invoice` | POST | 生成發票 PDF |
| `/functions/v1/export-transactions` | GET | 導出交易 CSV |

---

## 6. 部署流程（Deploy Flow）

### 6.1 Schema 部署
```bash
# 1. 連結 Supabase project
npx supabase login
npx supabase link --project-ref jnzdklfjdjmhjrhntljp

# 2. 部署 migrations
npx supabase db push

# 3. 或手動在 Studio 執行
# SQL Editor → paste migration file → Run
```

### 6.2 Application 部署
```bash
# 假設用 Node.js
npm run build
# 部署到 DigitalOcean VPS
# 或部署 Edge Functions
npx supabase functions deploy <function-name>
```

### 6.3 Backup 驗證
```bash
# 每日自動執行（見 backup-system/）
# GitHub Actions: daily-backup.yml
# VPS: daily-snapshot.sh
```

---

## 7. 安全模型（Security Model）

### 7.1 Row Level Security (RLS)

| Table | RLS Enabled | Policy |
|-------|------------|--------|
| buyers | ⚠️ 待確認 | 買手只看自己的行；Admin 全看 |
| customers | ⚠️ 待確認 | 同上 |
| orders | ⚠️ 待確認 | 買手看 assigned；客戶看自己的 |
| transactions | ⚠️ 待確認 | Admin 全看；其他人不可見 |
| refunds | ⚠️ 待確認 | Admin 全看 |
| audit_log | ⚠️ 待確認 | Admin 全看 |
| **以上全部** | **⚠️ 需盡快確認** | Run `recon/supabase-audit.sql` Section D |

### 7.2 Auth Flow（推測）

```
Telegram User ──→ Bot ──→ verify telegram_user_id ──→ Supabase Auth
                  ↑                              ↓
             JWT token                    RLS check via
             stored in                    auth.uid() or
             bot session                  JWT claims
```

---

## 8. 待確認清單（Confirmation Required）

> 請在 Supabase Studio 執行 `recon/supabase-audit.sql` 並把結果交給 AI 填寫。

- [ ] 24 張 table 的完整名單
- [ ] 每張 table 的 column 列表
- [ ] FK 關係圖
- [ ] RLS policy 狀態（Section D）
- [ ] Trigger 列表（Section E）
- [ ] Edge Functions 列表（Section F）
- [ ] Auth 方式（Supabase Auth 或 Telegram OAuth？）
- [ ] Bot code 的位置
- [ ] Admin web UI 是否存在
- [ ] 會計層（journal_entries）是否已實現

---

## 9. 緊急 Gap（立即行動）

| Gap | 嚴重度 | Action |
|-----|--------|--------|
| Schema 沒有本地 source | **災難級** | ✅ 已建立 `supabase/migrations/` |
| RLS 未確認 | **高** | Run `recon/supabase-audit.sql`，Section D |
| Audit log 不存在 | **高** | ✅ schema 已包含 placeholder |
| 會計層未實現 | **高** | ✅ schema 已包含框架，需 Priority 2 |

---

*最後更新：2026-05-23*
*Doc version: 1.0.0 — PLACEHOLDER*
