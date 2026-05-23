# BuyerOS（買手對象系統）— Gap Report

> 生成日期：2026-05-17
> Scope：審視「業務系統本體」嘅完整度，**唔包括** `backup-system/`（已完成）
> 方法：file system inventory + 用 backup file 入面嘅線索反推系統狀態

---

## TL;DR（畀冇耐性嘅你）

行入 `/Users/rubykan/Documents/Claude/Projects/買手對象系統` 一望，**整個 folder 入面除咗 `backup-system/` 之外，乜都冇**。冇 schema file、冇 frontend、冇 backend、冇 migration、冇 README、冇 `.env.example`、冇 `package.json`、冇 `deno.json`。即係 BuyerOS 嘅「應用本體」喺呢個 folder 入面 **唔存在 source-of-truth**。最大嗰個 gap 唔係會計，係 **整個 codebase / schema 喺本地完全唔可見**。如果今日 Supabase 個 project 出事，restore 返 DB 都唔知個 schema 之前點樣 evolve、邊個 RLS policy 點寫、Edge Function 邏輯點寫 —— 因為冇 source。

---

## A. 我見到嘅現況（factual inventory）

### A1. Folder 內容（完整）

```
買手對象系統/
└── backup-system/                    ← 上一 session 完成，已 skip audit
    ├── .gitkeep
    ├── README.md
    ├── SECRETS-CHECKLIST.md
    ├── SETUP-PROGRESS.md
    ├── .github/workflows/
    │   ├── daily-backup.yml
    │   └── storage-backup.yml
    └── scripts/
        ├── daily-snapshot.sh
        ├── health-check.sh
        └── restore-test.sh
```

Total：9 個 file，**全部都喺 `backup-system/`**。

### A2. 應有但**完全唔見**嘅 artifact

| 類別 | 應見到嘅 | 狀態 |
|---|---|---|
| Root README / project doc | `README.md`、`ARCHITECTURE.md`、`PRODUCT.md` | 冇 |
| Schema source | `schema.sql` / `prisma/schema.prisma` / `drizzle/schema.ts` / `supabase/migrations/*.sql` | 冇 |
| Frontend code | `app/`、`src/`、`pages/`、`web/`、`apps/web/` | 冇 |
| Backend code | `api/`、`server/`、`supabase/functions/`（Edge Functions） | 冇 |
| Bot code | 用戶 backup README 提到 Telegram bot 係主介面，應見 `bot/`、`telegram/`、`handlers/` | 冇 |
| Config | `package.json` / `deno.json` / `pnpm-workspace.yaml` / `Dockerfile` / `docker-compose.yml` | 冇 |
| Env template | `.env.example` / `.env.template` | 冇 |
| Migration history | `supabase/migrations/` / `db/migrations/` | 冇 |
| CI / Test | `.github/workflows/test.yml`、`tests/`、`__tests__/` | 冇 |
| RLS policy file | `supabase/policies/*.sql` 或同等 | 冇 |
| Seed data | `supabase/seed.sql` / `seed/` | 冇 |
| Type definition | `types/database.ts`（Supabase typegen 出嘅） | 冇 |

### A3. 從 `backup-system/` 反推到嘅事實（**確認**部分）

| 項目 | 數值 |
|---|---|
| Project 別名 | **BuyerOS** |
| Supabase project ref | `jnzdklfjdjmhjrhntljp` |
| VPS host | DigitalOcean droplet @ `206.189.116.155` |
| Storage 用緊 | Supabase Storage，bucket name = `documents` |
| Backup R2 bucket | `buyeros-backups` |
| Backup repo | `<user>/buyeros-backups` (GitHub) |
| Alert channel | Telegram bot（prod bot + alerts bot 分開） |
| 預期 DB tables | ≥ 20（用戶話 24 個） |
| Restore drill 入面標明嘅 critical tables | `buyers`、`transactions`、`refunds` |

### A4. 未能確認嘅嘢（直接認低威）

- 24 個 tables 嘅 **schema 結構、column、relation、constraint** —— 因為 schema source 唔喺 folder，亦冇 connect 緊 Supabase MCP（未 auth）
- Frontend / admin UI 用咩 framework（Next.js / Remix / SvelteKit / 純後台 SQL）
- Telegram bot 用咩 runtime（Node / Deno / Python / Edge Function）
- Auth provider：Supabase Auth？外部 Telegram OAuth？
- RLS policy 有冇開、邊啲 table 有
- Audit log table 存唔存在
- 有冇 payment gateway integration（Stripe / PayMe / 銀行轉帳手 reconcile）
- 月結 / 報表 而家係手做 SQL 定有 view / function 包裝
- Deployment 狀態：邊個 service running、邊個 service hardcode 喺 VPS

---

## B. 我推斷你嘅目標（基於現有線索）

從 backup 文件入面嘅措辭加你之前嘅 statement，我推斷個 BuyerOS 嘅 vision 大致係：

1. **業務模型**：你做緊一盤 「代購 / 採購中介 / 買手平台」生意。買手喺平台接單，幫客戶採購、收貨、交付，平台抽分潤；有客戶退貨 / refund flow；business volume 唔細（backup README 寫過「生意斷一日 = HK$500K」）。
2. **操作層**：而家主介面 likely 係 Telegram bot（客戶 + 買手 + 管理員），可能有少量 web admin。
3. **數據層**：24 個 table 都 host 喺 Supabase，包 buyer、transaction、refund、documents（單據 / 收據 storage）。
4. **會計層 ambition**：你想做「完整會計 + 月結」，即係超越「記返每單收咗幾錢」，去到 chart of accounts、journal entry、AR/AP、報表（試算表 / P&L / BS）、月結鎖賬呢個 level。
5. **Compliance / 災難意識**：你會主動 build backup SOP，講 HK$500K/day 機會成本 —— 即係呢盤生意對 system 嘅 reliability 要求係 **business-critical**，唔係 toy project。
6. **目前 self-rating**：你自己都覺得「會計 schema 拿不準」+「buyer 系統 build up 不夠完全」，即係你心入面已經感覺到 gap 喺：**(a) 會計部分嘅 schema design，(b) 業務 flow 嘅整體完整性**。

---

## C. Gap Matrix

> 嚴重度 logic：
> - **高** ＝ 出事直接傷生意 / 數據錯 / 客戶投訴 / compliance 爆煲
> - **中** ＝ 影響效率 / scale / 維護成本，但生意短期跑得郁
> - **低** ＝ Nice-to-have，可以後期再補

### C1. 系統基建層

| Component | 應有 | 現況 | 嚴重度 | 影響 | 建議下一步 |
|---|---|---|---|---|---|
| **Schema source-of-truth** | `supabase/migrations/*.sql` 入 git，每次 change 一個 migration file | 整個 folder 冇 schema file | **高** | 一旦 Supabase project 損壞或 mis-click，schema 改動歷史**永久丟失**；新人完全唔識個 system | 即刻喺 `/Users/rubykan/Documents/Claude/Projects/買手對象系統/` 開 `supabase/` folder，跑 `supabase db dump --schema public > supabase/migrations/0001_initial.sql`，commit 入 git |
| **Codebase 入 git** | 全 app（bot + web + functions）入 git，repo 有 README | 本 folder 完全唔見 app code | **高** | 冇版本管理＝改錯嘢無得 rollback；冇 code review；新 dev 接手成本 = 由零開始 | 確認你 app code 而家喺邊（其他 folder？Supabase Studio click 嘅 SQL？），全部 import 入呢個 folder 做 monorepo 或 multi-repo |
| **`.env.example`** | List 晒所有需要嘅 env var（唔填值） | 冇 | 中 | 新環境部署靠記憶；secret 容易漏 | 開一個 `.env.example`，照 backup-system 嘅 SECRETS-CHECKLIST 嗰份 list 抄落去 |
| **README at root** | 講清楚 system 大致 architecture、點 run、點 deploy | 冇 | 中 | Onboarding cost 高；自己半年後返嚟都唔記得點 setup | 寫一份 1-page `README.md`，標 stack / entry point / deploy 流程 |
| **Auth / RBAC** | Supabase Auth + role table，admin / buyer / customer 分開 | 未能確認 | 高（如果未做） | 客戶睇到唔屬於佢嘅 transaction = 大鑊 | 確認 RLS policy 開咗，每張 user-scoped table 都有 policy |
| **Audit log** | `audit_log` table 或 trigger-based change tracking | 未能確認 | 高（會計系統 must-have） | 退錢 / 改數查唔到邊個改、幾時改 → compliance 同內部信任都崩 | 加一張 `audit_log` table + 寫個 generic trigger 對 buyers / transactions / refunds / invoices |
| **Test / CI** | 至少 critical path（落單 / refund / 月結）有 test | 未能確認，folder 冇 test | 中 | 改一個 column 可能 break 月結都唔知 | 之後再補，先 fix 結構 |

### C2. 買手業務流層

| 業務 stage | 應有 table / function | 現況 | 嚴重度 | 影響 | 建議下一步 |
|---|---|---|---|---|---|
| **買手 onboarding** | `buyers`、`buyer_kyc`、`buyer_documents` | `buyers` 有（restore-test 提及），其餘未能確認 | 中 | KYC 唔齊 = 法律風險（特別跨境採購） | 確認 KYC field（HKID / passport / 銀行戶口）齊唔齊 |
| **接單 / 報名** | `orders`、`order_assignments`、`buyer_bids` | 未能確認 | 中 | 多買手搶單 / 分配機制冇 audit 就靠人肉 | List 而家 24 table，標出邊張 cover 接單 |
| **採購 / 收貨** | `procurement_items`、`receipts`、`logistics_events` | Storage bucket = `documents`，估係收據 / 單據 image；DB table 未能確認 | 中 | 收據文件 vs DB record 無 link = reconcile 困難 | 確認每張 receipt 有冇 `transaction_id` foreign key |
| **客戶交付** | `deliveries`、`delivery_proofs` | 未能確認 | 中 | 爭執時冇證據 | 同上，check schema |
| **結算 / 分潤** | `settlements`、`commission_rates`、`payouts` | 未能確認 | 高 | 算錯買手分潤 = 直接畀錢爭執 | 確認分潤 logic 寫喺 DB function 定 app layer，文檔化 |
| **退貨 / refund** | `refunds`（有！）+ `refund_reasons` + `refund_journal` | `refunds` 有 | 中 | 退款記得，但同會計 entry 唔同步，月結時唔對數 | Refund 一定要對應一條 journal entry（見 C3） |
| **評分 / 留人** | `ratings`、`reviews`、`buyer_performance` | 未能確認 | 低 | 短期唔影響，長期影響 buyer 質素 | 後期再補 |

### C3. 會計核心層（你自認「拿不準」嘅嗰部分）

| Component | 應有 | 現況 | 嚴重度 | 影響 | 建議下一步 |
|---|---|---|---|---|---|
| **Chart of Accounts（會計科目表）** | `accounts` table：account_code、account_name、type (asset/liability/equity/revenue/expense)、parent_id | 未能確認 | **高** | 冇 COA = 所有「會計」都係假會計，唔可能出 P&L / BS | 開一張 `accounts` table，按你業務 design 一個 minimal COA（cash、AR、AP、revenue-commission、refund-expense 起碼要有） |
| **Journal Entry（複式記賬）** | `journal_entries` + `journal_lines`（每 entry 至少 2 lines，debit = credit） | 未能確認 —— 如果 transactions 直接 record 收支但冇分錄，就唔係會計 | **高** | 出唔到試算表 = 月結基本上做唔到 | 設計 `journal_entries`（header: date / memo / source_type / source_id）+ `journal_lines`（entry_id / account_id / debit / credit），加一條 DB constraint：每個 entry 嘅 sum(debit) = sum(credit) |
| **AR（應收）/ AP（應付）** | `invoices`（客戶 invoice）+ `bills`（買手 / supplier bill）+ `payments` | 未能確認 | **高** | 你而家可能用 `transactions` 一張 table 撈晒 —— 結果 AR aging、AP aging 都做唔到 | 將 `transactions` 拆做 invoice / payment 兩個 concept；用 `invoices.status`（unpaid / partial / paid）追蹤 |
| **Invoice / Receipt PDF** | Invoice generator + PDF 存 R2 | Storage 有 `documents` bucket，但係 receipt 抑或 generated invoice 未能確認 | 中 | 客戶要正式 invoice 時靠手做 | Phase 2 再做 |
| **Tax（稅務）** | 香港冇 VAT/GST，但 profits tax 要有清晰 revenue / expense 分類；如果做跨境可能要 record VAT / customs duty 嘅 expense line | 未能確認 | 中 | 報利得稅 / 跨境合規 | 同會計師對一次：你個 COA 對唔對得返 IRD 嘅 schedule |
| **月結 / 鎖賬** | `accounting_periods` table（open / closed），closed period 嘅 entry 唔可以改 | 未能確認 | 高 | 唔鎖賬，舊 entry 隨時改 → 月結報表唔可信 | 開 `accounting_periods` + RLS policy：closed period 嘅 journal_lines INSERT/UPDATE/DELETE 一律 deny |
| **試算表 / 損益表 / 資產負債表** | SQL view 或 Edge Function，行一吓就出 | 未能確認 | 高 | 老闆問「上個月賺幾多」要逐單 SUM | 設計三個 view：`v_trial_balance`、`v_pnl`、`v_balance_sheet`，input 係 `period_id` |
| **Reconciliation** | 銀行 statement vs `payments` table 對數工具 | 未能確認 | 中 | 銀行少咗錢 / 多咗錢冇人察覺 | Phase 3 再做 |

### C4. System 對外 / 維運層

| Component | 應有 | 現況 | 嚴重度 | 影響 | 建議下一步 |
|---|---|---|---|---|---|
| **Notification（畀客戶）** | Telegram bot push + email fallback | Telegram bot 有，email 未能確認 | 中 | Telegram down 就無 channel 通知 | 加 email backup channel |
| **Search / Dashboard** | Admin dashboard 可以 search transaction / buyer | 未能確認 | 中 | 客服查單靠 SQL | 用 Supabase Studio 暫頂；長遠 build 簡單 admin web |
| **Export（CSV / Excel）** | 至少 transactions、journal_lines 可以 export 畀會計師 | 未能確認 | 中 | 報稅 / 外判會計師接駁困難 | 寫一個 Edge Function：input period，output CSV |
| **API doc** | OpenAPI / Postman collection | 未能確認 | 低 | 一個人 dev 短期唔礙事 | 後期 |
| **Immutability for backup（compliance）** | R2 Object Lock / WORM | 而家 R2 + GitHub Actions 可以 delete backup（backup README 自己提過） | 中 | 一旦做完整會計，audit-grade 要求 backup 不可篡改 | 開 R2 Object Lock，retention = 7 年（香港 IRD 標準） |

---

## D. 根源分析（Root cause）

呢啲 gap 嘅 root cause **唔係資源不足，係兩個更深層問題**：

### D1. Source-of-truth 散落問題（高佔比）
你 build BuyerOS 嘅方式好可能係「直接喺 Supabase Studio click table、寫 SQL、寫 RLS、寫 function」—— 即係 **DB 本身就係 source-of-truth，本地 folder 冇 mirror**。呢個係 Supabase 入門用家最常見嘅 pattern，但會 scale 唔到：

- 改錯野無得 git revert
- 災難 restore 之後，schema 雖然返到，但**邊個 commit 改咗咩 logic 完全冇 history**
- AI / 第二個人完全幫唔到手，因為冇 file 可以讀

**Fix 嘅 logic 唔係加 feature，係 export 現狀入 git**，建立 source-of-truth baseline。

### D2. 業務 model 同會計 model 未對齊（中佔比）
你自認「會計 schema 拿不準」嘅根源，係**買手平台嘅 transaction**（買手收咗錢、平台扣分潤、退款）同**會計嘅 journal entry**（每筆收支要 debit 一個 account / credit 一個 account）係**兩種 model**。如果你而家用 `transactions` 一張 table 又當業務記錄又當會計記錄，就會出現：

- 同一個 refund，可能要動 4 個 account（cash credit、refund expense debit、AR adjust、commission reversal），用一張 row 表達唔到
- 退完款，業務上 closed 咗，但會計上**反向 entry 未做**，月結對唔上

**Fix logic 係：business event ≠ accounting entry，要分開兩層**：buyer 平台保留原本嘅 `transactions / refunds` table 做業務記錄；上面 layer 一層 `journal_entries / journal_lines` 自動跟住業務事件 post 對應分錄。每張業務 row 有個 `journal_entry_id` foreign key 連去會計層。

### D3. 範圍未定（低佔比，但需要拍板）
「想做完整會計」嘅「完整」未定義：

- 係香港小公司 internal book（自己睇 + 報利得稅）？
- 定係要符合 HKFRS for SMEs / 畀外部 auditor 出 audit report？
- 定係要支援 multi-currency / 跨境？

呢個 scope 決定 schema 嘅複雜度，差好遠。**最 actionable 嘅一步：先 confirm 自己係邊一檔**。

---

## E. 優先建議（揀 3 個最值得即刻做嘅 gap）

### Priority 1 — 將 schema + code 入 git（½ 日 effort）
**做乜：**
1. 喺呢個 folder 開 `supabase/` subfolder
2. 跑 `npx supabase login` 然後 `npx supabase link --project-ref jnzdklfjdjmhjrhntljp`
3. 跑 `npx supabase db dump --schema public --file supabase/migrations/0001_initial.sql`
4. 跑 `npx supabase db dump --schema public --data-only --file supabase/seed.sql`（如果想連 reference data 都備份）
5. 將所有 Edge Function（如有）`npx supabase functions download <name>`
6. 將 Telegram bot code 同 admin code（無論而家喺邊度）全部 copy 入 folder
7. `git init && git add . && git commit -m "Initial source-of-truth import"`
8. Push 上 private GitHub repo

**點解優先：** 而家係 **single point of failure**。Supabase 掛咗、project 刪錯、有人 mis-click DROP TABLE —— restore 返 data 都唔知 schema 之前點寫嘅 RLS。呢一步 effort 最細、回報最大。

---

### Priority 2 — Design 會計層 schema（1-2 日 effort + 同會計師對一次）
**做乜：**
1. 揸枝筆喺白紙寫個 minimal COA（cash / bank / AR / AP / revenue-commission / refund-expense / supplier-cost / equity）
2. 開 3 張新 table：
   ```sql
   accounts (id, code, name, type, parent_id)
   journal_entries (id, entry_date, memo, source_type, source_id, period_id, posted_at, posted_by)
   journal_lines (id, entry_id, account_id, debit_cents, credit_cents)
   ```
3. 加 constraint：`CHECK (debit_cents = 0 OR credit_cents = 0)` + 每個 entry 用 trigger check `SUM(debit) = SUM(credit)`
4. 開 `accounting_periods` table，加 RLS：closed period 嘅 journal_lines 唔畀 modify
5. 寫 SQL function：`post_transaction_entry(transaction_id)` 自動由 business row 產生 journal entry
6. 寫 3 個 view：`v_trial_balance` / `v_pnl` / `v_balance_sheet`

**點解優先：** 你自己已經知呢度「拿不準」，呢個 gap 唔解決，做幾多 feature 都係追數追到頭都大；解決完之後，月結同報利得稅有 mechanical 答案。

---

### Priority 3 — 確認 RLS + audit log（½ 日 effort，但極之 critical）
**做乜：**
1. 跑呢條 SQL 確認所有 user-facing table 都有 RLS：
   ```sql
   SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public';
   ```
   任何 `rowsecurity = false` 嘅 user-facing table 都要立即補 policy
2. 開一張 `audit_log (id, table_name, row_id, action, old_data jsonb, new_data jsonb, changed_by, changed_at)`
3. 寫一條 generic trigger function，apply 落 `buyers / transactions / refunds / journal_entries / journal_lines / invoices`
4. 加 retention：90 日內熱數據留 DB，舊嘅 archive 入 R2

**點解優先：** RLS 漏一張 table = 客戶可以睇晒所有 transaction，係**privacy / 信譽** event。Audit log 缺失 = 月結 / refund 出爭執時冇證據。兩樣都係**唔做隨時爆煲**嘅嘢，但做完之後好少再 touch。

---

## F. 風險 / 注意事項

| 風險 | 嚴重度 | 機率 | 應對 |
|---|---|---|---|
| Schema 冇 source-of-truth，Supabase 出事後 restore 完都唔知 RLS / function 點寫 | 災難級 | 中（人類點錯掣 + 服務商 incident 都會發生） | Priority 1 一做完即時消除 |
| 會計 schema 唔對，年底報利得稅 / 畀會計師 sign 嘅時候要 **倒帶幾個月** 重做 entry | 高 | 高（你自己都覺得 schema 拿不準 = 已經感應到風險） | Priority 2 + 約會計師對 1 小時 COA |
| RLS 漏咗某張 table，客戶睇到其他客戶 data | 高 | 中（Supabase default `enable RLS` 但 user-created table 唔一定有 policy） | Priority 3 第一步即刻跑嗰條 SQL |
| 退款／分潤算錯，因為 logic 寫喺 app layer 唔喺 DB function，多個 entry point 唔同步 | 高 | 中 | Priority 2 過程中 review 哂分潤 logic 寫喺邊 |
| Backup 雖然 daily 跑，但 R2 backup file 仲可以 delete（backup README 自己講過唔係 audit-grade） | 中 | 低 | 做完會計層之後再開 R2 Object Lock / 7 年 retention |
| 客戶 / 買手 KYC 不齊，跨境採購遇到 customs / AML query 時答唔到 | 中 | 低 | 確認 KYC field 之後加 hard required |
| Telegram 係單一 channel，Telegram outage 時客戶連結唔到 | 中 | 低 | 後期加 email fallback |
| Application code 同 schema 散落幾個地方（Studio、其他 folder、本地 macOS），半年後自己都唔記得 | 中 | 高 | Priority 1 同時定 single source-of-truth folder |

---

## 附錄：未能確認 / 需要你 confirm 嘅嘢

請你回答以下嘢，我先可以將呢份 Gap Report 由「推斷」變「確認」：

1. App code（Telegram bot handler / admin / Edge Function）而家**實際**喺邊個 folder？定 Supabase Studio 上手寫？
2. 24 個 table 嘅 name list（隨手畀我一個 `\dt` 或 Supabase Studio screenshot 都得）
3. Auth 用 Supabase Auth 定 Telegram OAuth？
4. 而家有冇任何 form of audit log？
5. 「完整會計」嘅 scope —— 自己 internal 用 / 報利得稅 / 畀外部 auditor sign？
6. 業務量 rough size：月成交單數、月 GMV、買手人數？（呢個影響 schema 複雜度選擇）

---

> 寫完。下一步建議：先做 Priority 1（schema 入 git），再坐落嚟同我傾 Priority 2 嘅 COA design。
