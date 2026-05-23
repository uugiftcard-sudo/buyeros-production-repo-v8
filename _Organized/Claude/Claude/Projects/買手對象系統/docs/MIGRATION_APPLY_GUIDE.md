# Migration Apply Guide（遷移部署指引）

> 日期：2026-05-23
> 適用於：Buyeros Supabase Project `jnzdklfjdjmhjrhntljp`

---

## ⚠️ Apply 前必讀

**任何 Migration 都建議先在 TEST 環境跑一次！**

Supabase Dashboard → 複製 Project → 改名為 `buyeros-test` → 測試完再 apply 到 prod。

---

## Migration 執行順序

```
0001 → 0002 → 0002b → 0003
```

| Order | File | 作用 |
|-------|------|------|
| 1 | `0001_initial_reconstructed.sql` | **Placeholder** — 先替換成真實 schema dump |
| 2 | `0002_accounting_layer.sql` | 會計層核心（COA、Journal、Period、Views） |
| 3 | `0002b_config_driven_posting.sql` | 配置驅動自動記賬（可選，建議裝） |
| 4 | `0003_rls_and_audit.sql` | RLS policies + audit log |

---

## 步驟 1：替換 0001 為真實 Schema

### 1a. 安裝 Supabase CLI
```bash
# macOS
brew install supabase/tap/supabase

# 或
npm install -g supabase
```

### 1b. 連結 Project
```bash
npx supabase login
npx supabase link --project-ref jnzdklfjdjmhjrhntljp
```

### 1c. Dump 真實 Schema
```bash
npx supabase db dump --schema public > supabase/migrations/0001_initial.sql
```

### 1d. 確認 Dump 內容
```bash
# 檢查有冇 transactions、refunds、buyers、orders table
grep -c "CREATE TABLE" supabase/migrations/0001_initial.sql
```

### 1e. 比較差異
```bash
# 確認 0001 包含的核心 table
grep -E "CREATE TABLE.*(transactions|refunds|buyers|orders|customers)" \
  supabase/migrations/0001_initial.sql
```

---

## 步驟 2：驗證 Enum 值

在 Supabase Studio SQL Editor 執行 `recon/check-enums.sql`

```bash
# 確認以下值（然後更新 0002b_config_driven_posting.sql 的 seed data）
SELECT DISTINCT type FROM transactions;
SELECT DISTINCT status FROM refunds;
```

### 對照表（如果 enum 值不同，修改 `event_value`）

| 預設值 | 你的實際值（填入） |
|--------|-------------------|
| `deposit` | ____ |
| `payment` | ____ |
| `balance` | ____ |
| `commission` | ____ |
| `failed` | ____ |
| `approved` | ____ |
| `processing` | ____ |
| `completed` | ____ |

---

## 步驟 3：在 Test 環境 Apply

### 3a. 開 Test Project（一次性）
Supabase Dashboard → New Project → 命名 `buyeros-test`

### 3b. Apply Migrations
```bash
npx supabase db push --project-ref <test-project-ref>
```

或直接在 Supabase Studio SQL Editor 逐個 paste：

1. `0001_initial.sql`（真實 schema）→ Run
2. `0002_accounting_layer.sql` → Run
3. `0002b_config_driven_posting.sql` → Run
4. `0003_rls_and_audit.sql` → Run

### 3c. 驗證 Apply 結果
```sql
-- Check all tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- Check views
SELECT table_name FROM information_schema.views
WHERE table_schema = 'public';

-- Check RLS
SELECT * FROM recon_rls_audit();

-- Check COA seeded
SELECT COUNT(*) AS account_count FROM accounts;

-- Check Trial Balance
SELECT * FROM v_trial_balance LIMIT 10;
```

### 3d. 跑功能測試
```sql
-- Test journal posting
-- 1. Insert a test transaction (if data exists)
-- 2. Check if journal entry auto-created

-- Test backfill
SELECT * FROM backfill_journal_entries();

-- Test period lock
UPDATE accounting_periods SET status = 'closed' WHERE period_name = '2026-05';
-- Now try to insert journal entry in closed period → should fail
```

---

## 步驟 4：Apply 到 Prod

### 4a. 確認
- Test 環境全部 pass
- 備份已執行（見 backup-system）

### 4b. Apply
```bash
npx supabase db push --project-ref jnzdklfjdjmhjrhntljp
```

或逐個 paste migration（見 3b）

### 4c. 觀察
Apply 後頭 24 小時密切觀察：
- Supabase Dashboard → Logs
- Telegram bot 有冇異常
- 新 transactions 有冇正常 post journal entries

---

## 步驟 5：驗證 Prod

```sql
-- RLS audit
SELECT * FROM recon_rls_audit();

-- Check journal entries being created
SELECT COUNT(*) AS je_count FROM journal_entries;

-- Check trial balance
SELECT * FROM v_trial_balance;

-- Check audit log working
SELECT * FROM audit_log LIMIT 5;
```

---

## 常見問題

| 問題 | 解決 |
|------|------|
| `Table already exists` | 0001 和現有 schema 重疊 — 跳過 0001，直接 apply 0002/0003 |
| `account_code not found` | COA seed 未執行 — 手動 INSERT accounts |
| `debit != credit` error | Rule 設定錯 — 修正 `journal_posting_rules` |
| `RLS blocking access` | 用 service_role key，或 disable RLS temporarily |

---

*最後更新：2026-05-23*
