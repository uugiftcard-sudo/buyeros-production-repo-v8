# P2: 會計層 Schema 設計文檔

> 對應：`supabase/migrations/0002_accounting_layer.sql`
> 日期：2026-05-23
> 目的：將「業務記錄」轉化為「可審計的複式記賬系統」

---

## 1. 設計原則

### 1.1 業務事件 ≠ 會計分錄（兩層分開）

```
┌─────────────────────┐     Trigger     ┌──────────────────────┐
│   Business Tables   │ ────────────→  │  Accounting Tables   │
│                     │                │                      │
│  transactions       │                │  journal_entries     │
│  refunds            │                │  journal_lines       │
│  settlements        │                │  accounts            │
└─────────────────────┘                └──────────────────────┘
```

- **業務層（Tier 1-3）**：記錄「發生了什麼」
- **會計層（Tier 4）**：記錄「錢去了哪個 account」

好處：
- 業務層可以快速 query（`SELECT * FROM orders WHERE status = 'pending'`）
- 會計層保證 debit = credit，任何人都可以驗證
- 兩層獨立，審計時可以 cross-reference

### 1.2 Debit / Credit 方向圖

| Account Type | Debit 效果 | Credit 效果 |
|-------------|-----------|-----------|
| Asset（資產） | ↑ 增加 | ↓ 減少 |
| Liability（負債）| ↓ 減少 | ↑ 增加 |
| Equity（權益）| ↓ 減少 | ↑ 增加 |
| Revenue（收入）| ↓ 減少 | ↑ 增加 |
| Expense（支出）| ↑ 增加 | ↓ 減少 |

### 1.3 Cents-only（整數）

所有金額以 `INT cents` 儲存，**不使用** `NUMERIC` 或 `FLOAT`。
理由：
- 完全避免 0.1 + 0.2 = 0.30000000000000004 問題
- HKD 最小單位是 1 仙（0.01）
- PostgreSQL INT 運算最快

---

## 2. Chart of Accounts（會計科目表）

### 2.1 Account Code 結構

四碼結構：`XXXX`
- `1xxx`：資產（Asset）
- `2xxx`：負債（Liability）
- `3xxx`：權益（Equity）
- `4xxx`：收入（Revenue）
- `5xxx`：支出（Expense）

### 2.2 完整 COA 清單

| Code | 中文名 | 英文名 | Type | 用途 |
|------|--------|--------|------|------|
| **1101** | 銀行戶口 — HSBC | HSBC Bank Account | Asset | 主要收支戶口 |
| **1102** | 銀行戶口 — 其他 | Other Bank Account | Asset | 備用戶口 |
| **1109** | 零用現金 | Petty Cash | Asset | 小額現金 |
| **1201** | 應收帳款 — 客戶 | AR Customers | Asset | 客戶未付款 |
| **1202** | 應收帳款 — 買手 | AR Buyers | Asset | 買手欠款 |
| **1301** | 在途貨品 | Goods in Transit | Asset | 採購中未到貨 |
| **1302** | 預付款項 | Prepayments | Asset | 預付費用 |
| **2101** | 應付帳款 — 供應商 | AP Suppliers | Liability | 欠供應商 |
| **2102** | 應付帳款 — 買手結算 | AP Buyer Settlement | Liability | 買手墊支待結 |
| **2201** | 應繳利得稅 | Profits Tax Payable | Liability | IRD 應繳 |
| **2301** | 暫收款項 | Suspense Receipts | Liability | 未確認款項 |
| **3101** | 實繳資本 | Paid-in Capital | Equity | 初始投入 |
| **3102** | 保留盈利 | Retained Earnings | Equity | 歷史利潤滾存 |
| **3103** | 本期損益 | Current Year P&L | Equity | 當年累計盈虧 |
| **4101** | 代購服務費收入 | Procurement Service Revenue | Revenue | 主要收入（分潤） |
| **4102** | 手續費收入 | Handling Fee Revenue | Revenue | 附加手續費 |
| **4201** | 利息收入 | Interest Income | Revenue | 被動收入 |
| **5101** | 採購成本 | Procurement Cost | Expense | 墊支採購款 |
| **5102** | 退貨成本 | Cost of Refunds | Expense | 退貨相關成本 |
| **5201** | 退款支出 | Refund Expenses | Expense | 退款產生的損失 |
| **5202** | 平台運營支出 | Platform Operating Expenses | Expense | 日常運營 |
| **5301** | 銀行費用 | Bank Charges | Expense | 轉帳手續費 |
| **5401** | 利得稅支出 | Profits Tax Expense | Expense | 實際繳納利得稅 |

---

## 3. Journal Entry 流程

### 3.1 Entry Number 格式

```
JE-YYYY-MM-NNNN
Example: JE-2026-05-0001
```

- `JE`：固定前綴
- `YYYY-MM`：年月
- `NNNN`：該月第 N 個 entry（自動遞增）

### 3.2 典型業務 → 分錄映射

#### 客戶付款（Customer Payment）
```
# 假設：客戶支付 HK$1,000 服務費

借：1101 銀行戶口         HK$1,000
貸：4101 代購服務費收入    HK$1,000

Journal Entry:
  source_type: transaction
  source_ref:  TXN-2026-05-0001
  memo: Customer payment received: TXN-2026-05-0001
```

#### 退款（Refund）
```
# 假設：退款 HK$500

借：5201 退款支出         HK$500
貸：1101 銀行戶口         HK$500

Journal Entry:
  source_type: refund
  memo: Refund processed: REF-2026-05-0001 — quality issue
```

#### 月結（Month-End Close）
```
# 月結時，收入轉入本期損益

借：4101 代購服務費收入    HK$10,000
貸：3103 本期損益         HK$10,000

Journal Entry:
  source_type: manual
  memo: Month-end close: transfer revenue to P&L (2026-05)
```

### 3.3 自動 Post 機制

Trigger 安裝在 `transactions` 和 `refunds` 表：
- `transactions` INSERT/UPDATE → `post_transaction_journal()`
- `refunds` UPDATE（pending → approved）→ `post_refund_journal()`

⚠️ **限制**：目前假設 `transactions.type` 包含 `'payment', 'deposit', 'balance', 'commission'`。
需要驗證實際 schema 後調整 `CASE` 語句。

---

## 4. 月結流程（Month-End Close）

### 4.1 月結步驟

```
1. 確認所有交易已錄入 journal_entries
2. 執行：SELECT close_accounting_period('2026-05');
3. 系統自動：
   a. 鎖定 period（UPDATE accounting_periods SET status='closed'）
   b. 產生 closing entry（Revenue → 3103 本期損益）
4. 確認試算表 balance
5. 輸出月報（v_pnl_summary, v_trial_balance）
```

### 4.2 Period Lock 保護

一旦 period 設為 `closed`：
- `journal_lines` INSERT/UPDATE/DELETE → **拒絕**
- `journal_entries` UPDATE/DELETE → **拒絕**
- 唯一修正方法：先 `UPDATE accounting_periods SET status='open'`（需要 admin）

---

## 5. 報表使用方式

### 5.1 試算表（Trial Balance）
```sql
SELECT * FROM v_trial_balance;
-- 輸出：所有 account 的 debit/credit 總計及餘額
```

### 5.2 月度損益表
```sql
SELECT * FROM v_monthly_pnl ORDER BY period, category;
-- 按月輸出：收入 / 支出 明細
```

### 5.3 P&L 摘要
```sql
SELECT * FROM v_pnl_summary ORDER BY period, sort_order;
-- Revenue / Expenses / Net Profit 三行
```

### 5.4 資產負債表
```sql
SELECT * FROM v_balance_sheet('2026-05-31');
-- 指定日期的 BS snapshot
```

### 5.5 應收帳齡
```sql
SELECT * FROM v_ar_aging;
-- 顯示邊個客戶拖數
```

---

## 6. 與香港利得稅的對應

| IRD 申報要求 | COA 對應 | 備注 |
|------------|---------|------|
| 營業額 | 4101 + 4102 + 4201 | Revenue accounts |
| 銷售成本 | 5101 + 5102 | Expense accounts |
| 支出 | 5201 + 5202 + 5301 | 運營支出 |
| 銀行存款 | 1101 + 1102 | BS Asset |
| 應收款 | 1201 + 1202 | BS Asset |
| 應付款 | 2101 + 2102 | BS Liability |
| 利得稅 | 2201 + 5401 | Liability + Expense |

---

## 7. 待確認 / 需要用戶行動的事項

- [ ] **確認 transactions.type enum**：目前假設包含 payment/deposit/balance/commission
- [ ] **確認 refunds.status enum**：目前假設包含 pending/approved/processing/completed/rejected
- [ ] **對 COA 過目**：與會計師對一次，確認沒有遺漏業務相關的 account
- [ ] **確認首個會計年度開始日期**：目前 hardcode 為 2024-01-01，需確認
- [ ] **歷史數據遷移**：已存在的 transactions 是否需要 backfill journal entries？

---

## 8. 附：Scope 決策

### 香港小公司 Internal Book vs 完整 Auditor Report

本設計對應 **internal book** 等級（自己睇 + 報利得稅）。

如果未來需要 **auditor-grade**：
- 需要增加：`fixed_asset_register`、`depreciation_schedule`、`intercompany_elimination`、`cash_flow_statement`
- `audit_log`（P3）需要升級為不可篡改的 append-only log

如需 **multi-currency**（USD / CNY）：
- `journal_lines` 需加 `currency` 和 `exchange_rate` 欄位
- 增加 `exchange_gain_loss` account（4202）

---

*設計日期：2026-05-23*
*P2 完成後，請對照 ARCHITECTURE.md 更新第 3 節 Data Model*
