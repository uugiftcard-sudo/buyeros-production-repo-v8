# Rollback 策略

> 任何破壞性 Migration 前請先做 Snapshot。
> 見 `backup-system/` 的完整 backup SOP。

---

## Migration Rollback 對照表

| Migration | 破壞性操作 | Rollback 方法 |
|---------|-----------|-------------|
| `0001_initial_reconstructed.sql` | CREATE TABLE | `DROP TABLE IF EXISTS <name> CASCADE;` |
| `0002_accounting_layer.sql` | CREATE TABLE, CREATE VIEW, CREATE TRIGGER | 按順序 DROP |
| `0002b_config_driven_posting.sql` | CREATE TABLE, CREATE FUNCTION | DROP |
| `0003_rls_and_audit.sql` | ENABLE RLS, audit triggers | 按順序 DISABLE |

---

## Rollback SQL（按 Migration 分組）

### 0003 Rollback（先做）

```sql
-- Disable audit triggers
DROP TRIGGER IF EXISTS trg_buyers_audit ON buyers;
DROP TRIGGER IF EXISTS trg_customers_audit ON customers;
DROP TRIGGER IF EXISTS trg_orders_audit ON orders;
DROP TRIGGER IF EXISTS trg_transactions_audit ON transactions;
DROP TRIGGER IF EXISTS trg_refunds_audit ON refunds;
DROP TRIGGER IF EXISTS trg_settlements_audit ON settlements;
DROP TRIGGER IF EXISTS trg_journal_entries_audit ON journal_entries;

-- Drop audit trigger function
DROP FUNCTION IF EXISTS log_audit_event();

-- Disable RLS
ALTER TABLE buyers          DISABLE ROW LEVEL SECURITY;
ALTER TABLE customers      DISABLE ROW LEVEL SECURITY;
ALTER TABLE orders         DISABLE ROW LEVEL SECURITY;
ALTER TABLE transactions   DISABLE ROW LEVEL SECURITY;
ALTER TABLE refunds        DISABLE ROW LEVEL SECURITY;
ALTER TABLE settlements    DISABLE ROW LEVEL SECURITY;
ALTER TABLE documents      DISABLE ROW LEVEL SECURITY;
ALTER TABLE invoices       DISABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries DISABLE ROW LEVEL SECURITY;
ALTER TABLE journal_lines  DISABLE ROW LEVEL SECURITY;
ALTER TABLE accounts      DISABLE ROW LEVEL SECURITY;
ALTER TABLE accounting_periods DISABLE ROW LEVEL SECURITY;

-- Drop audit log (⚠️ DATA LOSS)
DROP TRIGGER IF EXISTS trg_audit_log_no_update ON audit_log;
DROP TRIGGER IF EXISTS trg_audit_log_no_delete ON audit_log;
DROP FUNCTION IF EXISTS prevent_audit_log_modification();
DROP TABLE IF EXISTS audit_log;

-- Drop RLS audit function
DROP FUNCTION IF EXISTS recon_rls_audit();
```

### 0002b Rollback

```sql
DROP FUNCTION IF EXISTS post_all_pending_journal_entries();
DROP FUNCTION IF EXISTS backfill_journal_entries(UUID);
DROP FUNCTION IF EXISTS apply_journal_rule(TEXT, UUID);
DROP FUNCTION IF EXISTS get_account_id(TEXT);
DROP TABLE IF EXISTS journal_posting_rules;
```

### 0002 Rollback（最後做）

```sql
-- Drop views
DROP VIEW IF EXISTS v_ar_aging;
DROP VIEW IF EXISTS v_pnl_summary;
DROP VIEW IF EXISTS v_monthly_pnl;
DROP VIEW IF EXISTS v_trial_balance;

-- Drop balance sheet function
DROP FUNCTION IF EXISTS v_balance_sheet(DATE);

-- Drop close procedure
DROP FUNCTION IF EXISTS close_accounting_period(TEXT);

-- Drop journal trigger functions
DROP TRIGGER IF EXISTS trg_lock_closed_period ON journal_lines;
DROP TRIGGER IF EXISTS trg_lock_closed_journal_entries ON journal_entries;
DROP FUNCTION IF EXISTS lock_period_journal_lines();
DROP FUNCTION IF EXISTS lock_period_journal_entries();

DROP TRIGGER IF EXISTS trg_enforce_entry_balance ON journal_lines;
DROP FUNCTION IF EXISTS enforce_entry_balance();

DROP TRIGGER IF EXISTS trg_journal_entry_derive_period ON journal_entries;
DROP FUNCTION IF EXISTS derive_period_from_date();

-- Drop journal trigger functions (from 0002)
DROP TRIGGER IF EXISTS trg_post_transaction_journal ON transactions;
DROP TRIGGER IF EXISTS trg_post_refund_journal ON refunds;
DROP FUNCTION IF EXISTS post_transaction_journal();
DROP FUNCTION IF EXISTS post_refund_journal();

-- Drop tables (⚠️ DATA LOSS — journal entries will be deleted)
DROP TABLE IF EXISTS journal_lines CASCADE;
DROP TABLE IF EXISTS journal_entries CASCADE;
DROP TABLE IF EXISTS accounting_periods CASCADE;
DROP TABLE IF EXISTS accounts CASCADE;
```

---

## 緊急 Rollback（完整恢復）

如果 Migration apply 後出現問題：

```bash
# 1. Restore from Supabase pg_dump backup
psql "postgresql://postgres:<password>@db.jnzdklfjdjmhjrhntljp.supabase.co:5432/postgres" \
  < backups/latest.sql

# 2. Or restore specific table from R2 backup
# See backup-system/restore-test.sh
```

---

## 安全原則

1. **永遠先 Snapshot / pg_dump**
2. **先在 Test 環境試 Rollback**
3. **Production Rollback 只能在緊急情況下做**
4. **Rollback 後立即通知相關人**
5. **記錄 Rollback 原因和時間**

---

*最後更新：2026-05-23*
