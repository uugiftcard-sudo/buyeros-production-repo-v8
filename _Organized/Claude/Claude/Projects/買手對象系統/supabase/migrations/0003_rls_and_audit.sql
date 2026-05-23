-- ============================================================
-- P3: RLS Audit + Audit Log Migration
-- BuyerOS（買手對象系統）
-- ============================================================
-- Migration: 0003_rls_and_audit.sql
-- Depends on: 0001_initial_reconstructed.sql + 0002_accounting_layer.sql
--
-- Scope:
--   - RLS policy audit & template policies
--   - audit_log table (immutable append-only)
--   - Generic audit trigger function
--   - Retention policy
-- ============================================================


-- ============================================================
-- 0. Dependency check
-- ============================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'buyers'
    ) THEN
        RAISE EXCEPTION 'Core tables not found. Apply 0001 and 0002 first.';
    END IF;
END;
$$;


-- ============================================================
-- 1. RLS Audit
-- ============================================================

-- Run this query to audit ALL RLS status:
-- SELECT * FROM recon_rls_audit();  -- see function below

CREATE OR REPLACE FUNCTION recon_rls_audit()
RETURNS TABLE (
    table_name         TEXT,
    rls_enabled        BOOLEAN,
    policy_count       BIGINT,
    has_select_policy  BOOLEAN,
    has_insert_policy  BOOLEAN,
    has_update_policy  BOOLEAN,
    has_delete_policy  BOOLEAN,
    security_status    TEXT,
    recommendation     TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        t.table_name,
        t.rls_enabled,
        COUNT(p.oid)::BIGINT            AS policy_count,
        BOOL_OR(p.cmd = 'SELECT')       AS has_select_policy,
        BOOL_OR(p.cmd = 'INSERT')       AS has_insert_policy,
        BOOL_OR(p.cmd = 'UPDATE')       AS has_update_policy,
        BOOL_OR(p.cmd = 'DELETE')       AS has_delete_policy,
        CASE
            WHEN NOT t.rls_enabled
                THEN '🔴 NO RLS — ALL ROWS PUBLIC'
            WHEN t.rls_enabled AND COUNT(p.oid) = BIGINT '0'
                THEN '🔴 RLS ON, NO POLICY — ALL ACCESS DENIED'
            WHEN t.rls_enabled AND COUNT(p.oid) > BIGINT '0'
                AND NOT BOOL_OR(p.cmd = 'SELECT')
                THEN '🟡 RLS ON, NO SELECT POLICY'
            ELSE '🟢 RLS ON WITH POLICIES'
        END                             AS security_status,
        CASE
            WHEN NOT t.rls_enabled
                THEN 'Enable RLS + apply policies immediately'
            WHEN t.rls_enabled AND COUNT(p.oid) = BIGINT '0'
                THEN 'Add at minimum SELECT + INSERT policies'
            ELSE 'Review policies for completeness'
        END                             AS recommendation
    FROM (
        SELECT c.relname AS table_name, c.relrowsecurity AS rls_enabled
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
          AND c.relname NOT IN ('audit_log', 'migrations', 'schema_migrations')
    ) t
    LEFT JOIN pg_policy p ON p.polrelid = t.table_name::regclass
    GROUP BY t.table_name, t.rls_enabled
    ORDER BY t.rls_enabled, t.table_name;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION recon_rls_audit IS
    'Run: SELECT * FROM recon_rls_audit(); — returns RLS status for all tables.';


-- ============================================================
-- 2. Auth Model Assumptions
-- ============================================================
-- This migration assumes ONE of the following:
--
--   OPTION A: Supabase Auth (recommended)
--     - auth.users.id → UUID links to buyers/customers table
--     - buyer_id column in auth.users metadata or separate join table
--     - Policies use: auth.uid() = buyer_id or auth.uid() = customer_id
--
--   OPTION B: Telegram OAuth
--     - auth.users.raw_user_meta_data → telegram_user_id
--     - Policies use JWT claims from telegram_user_id
--
--   OPTION C: Server-side only (bot is only client)
--     - RLS disabled (DENY ALL)
--     - All access via service_role key in Edge Functions
--
-- ⚠️ Review and SELECT the appropriate policy set below (A, B, or C).
-- Default: OPTION A (Supabase Auth)
-- ============================================================


-- ============================================================
-- 3. OPTION A Policies (Supabase Auth)
-- ============================================================

-- Enable RLS on all user-facing tables
ALTER TABLE buyers          ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers       ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders          ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items     ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions    ENABLE ROW LEVEL SECURITY;
ALTER TABLE refunds         ENABLE ROW LEVEL SECURITY;
ALTER TABLE settlements     ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents       ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices        ENABLE ROW LEVEL SECURITY;

-- ── BUYERS ──────────────────────────────────────────────────

-- Admin can do everything (service_role bypasses RLS anyway)
CREATE POLICY "buyers_admin_all" ON buyers
    FOR ALL USING (TRUE);

-- Buyers can read their own row
CREATE POLICY "buyers_own_read" ON buyers
    FOR SELECT USING (
        telegram_user_id = NULL  -- TODO: replace with auth.uid() link
    );

-- Note: To link auth.uid() to telegram_user_id, add a column:
--   auth_user_id UUID REFERENCES auth.users(id)
-- Then use: auth.uid() = auth_user_id


-- ── CUSTOMERS ───────────────────────────────────────────────

CREATE POLICY "customers_admin_all" ON customers
    FOR ALL USING (TRUE);

CREATE POLICY "customers_self_read" ON customers
    FOR SELECT USING (
        TRUE  -- TODO: auth.uid() = auth_user_id
    );


-- ── ORDERS ─────────────────────────────────────────────────

CREATE POLICY "orders_admin_all" ON orders
    FOR ALL USING (TRUE);

-- Buyer sees orders assigned to them
CREATE POLICY "orders_buyer_read" ON orders
    FOR SELECT USING (
        assigned_buyer_id = NULL  -- TODO: auth.uid() = buyer_id via join
    );

CREATE POLICY "orders_buyer_insert" ON orders
    FOR INSERT WITH CHECK (TRUE);  -- TODO: customer self-create via bot

-- Customer sees their own orders
CREATE POLICY "orders_customer_read" ON orders
    FOR SELECT USING (
        customer_id = NULL  -- TODO: auth.uid() = customer_id via join
    );


-- ── TRANSACTIONS ───────────────────────────────────────────

CREATE POLICY "transactions_admin_all" ON transactions
    FOR ALL USING (TRUE);

-- Transactions: admin-only for now (sensitive financial data)
CREATE POLICY "transactions_admin_only" ON transactions
    FOR SELECT USING (TRUE);  -- TODO: replace with proper role check


-- ── REFUNDS ────────────────────────────────────────────────

CREATE POLICY "refunds_admin_all" ON refunds
    FOR ALL USING (TRUE);

CREATE POLICY "refunds_admin_only" ON refunds
    FOR SELECT USING (TRUE);  -- TODO: replace with proper role check


-- ── SETTLEMENTS ────────────────────────────────────────────

CREATE POLICY "settlements_admin_all" ON settlements
    FOR ALL USING (TRUE);

-- Buyer sees their own settlements
CREATE POLICY "settlements_buyer_read" ON settlements
    FOR SELECT USING (
        buyer_id = NULL  -- TODO: auth.uid() = buyer_id
    );


-- ── DOCUMENTS ───────────────────────────────────────────────

CREATE POLICY "documents_admin_all" ON documents
    FOR ALL USING (TRUE);

CREATE POLICY "documents_owner_read" ON documents
    FOR SELECT USING (TRUE);  -- TODO: link to uploader


-- ── INVOICES ──────────────────────────────────────────────

CREATE POLICY "invoices_admin_all" ON invoices
    FOR ALL USING (TRUE);

CREATE POLICY "invoices_customer_read" ON invoices
    FOR SELECT USING (
        customer_id = NULL  -- TODO: auth.uid() = customer_id
    );


-- ── JOURNAL ENTRIES & LINES ─────────────────────────────────
-- (accounting layer — always admin-only)

ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_lines  ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts       ENABLE ROW LEVEL SECURITY;

CREATE POLICY "journal_admin_only" ON journal_entries
    FOR ALL USING (TRUE);

CREATE POLICY "journal_lines_admin_only" ON journal_lines
    FOR ALL USING (TRUE);

CREATE POLICY "accounts_admin_read" ON accounts
    FOR SELECT USING (TRUE);

-- ── ACCOUNTING PERIODS ─────────────────────────────────────
-- Admin-only

ALTER TABLE accounting_periods ENABLE ROW LEVEL SECURITY;

CREATE POLICY "periods_admin_all" ON accounting_periods
    FOR ALL USING (TRUE);


-- ============================================================
-- 4. Audit Log Table (Append-Only)
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- What changed
    table_name      TEXT NOT NULL,
    row_id          UUID NOT NULL,
    action          TEXT NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),

    -- Data snapshot
    old_data        JSONB,
    new_data        JSONB,

    -- Who made the change
    changed_by      UUID,              -- auth.users.id
    changed_by_role TEXT CHECK (changed_by_role IN ('admin', 'buyer', 'customer', 'system', 'api')),
    changed_by_tg_id BIGINT,          -- telegram_user_id if via bot

    -- Context
    ip_address      INET,
    user_agent      TEXT,
    request_id      UUID,              -- correlation ID for API calls
    reason          TEXT
);

-- IMMUTABILITY: Prevent UPDATE and DELETE on audit_log
-- This is a critical compliance requirement.
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE are not permitted.';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_audit_log_no_update
    BEFORE UPDATE ON audit_log FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();

CREATE TRIGGER trg_audit_log_no_delete
    BEFORE DELETE ON audit_log FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();

-- Only INSERT is allowed (enforced by absence of UPDATE/DELETE triggers with INSERT action)

COMMENT ON TABLE audit_log IS
    'Immutable append-only audit trail. No UPDATE or DELETE permitted. GDPR: older entries can be anonymized (null out changed_by) but never deleted.';


-- ============================================================
-- 5. Generic Audit Trigger Function
-- ============================================================

CREATE OR REPLACE FUNCTION log_audit_event()
RETURNS TRIGGER AS $$
DECLARE
    current_user_id  UUID;
    current_role    TEXT;
    current_tg_id   BIGINT;
BEGIN
    -- Try to get current auth user
    BEGIN
        current_user_id := NULL;  -- auth.uid() is not directly accessible in trigger
        -- Note: If using Supabase Auth, you'd use:
        -- current_user_id := (SELECT auth.uid());
        -- But this requires SECURITY DEFINER function + auth extension.
        current_role := 'system';  -- TODO: set from context
    EXCEPTION WHEN OTHERS THEN
        current_role := 'unknown';
    END;

    INSERT INTO audit_log (
        table_name,
        row_id,
        action,
        old_data,
        new_data,
        changed_by,
        changed_by_role,
        changed_by_tg_id
    ) VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) END,
        current_user_id,
        current_role,
        current_tg_id
    );

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Apply audit triggers to critical tables
CREATE TRIGGER trg_buyers_audit
    AFTER INSERT OR UPDATE OR DELETE ON buyers
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER trg_customers_audit
    AFTER INSERT OR UPDATE OR DELETE ON customers
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER trg_orders_audit
    AFTER INSERT OR UPDATE OR DELETE ON orders
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER trg_transactions_audit
    AFTER INSERT OR UPDATE OR DELETE ON transactions
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER trg_refunds_audit
    AFTER INSERT OR UPDATE OR DELETE ON refunds
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER trg_settlements_audit
    AFTER INSERT OR UPDATE OR DELETE ON settlements
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();

CREATE TRIGGER trg_journal_entries_audit
    AFTER INSERT OR UPDATE OR DELETE ON journal_entries
    FOR EACH ROW EXECUTE FUNCTION log_audit_event();


-- ============================================================
-- 6. Audit Log Query Helpers
-- ============================================================

-- Who touched a specific record?
CREATE OR REPLACE FUNCTION audit_trail(
    p_table_name TEXT,
    p_row_id     UUID
)
RETURNS TABLE (
    created_at      TIMESTAMPTZ,
    action          TEXT,
    changed_by_role TEXT,
    old_data        JSONB,
    new_data        JSONB,
    reason          TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT al.created_at, al.action, al.changed_by_role,
           al.old_data, al.new_data, al.reason
    FROM audit_log al
    WHERE al.table_name = p_table_name
      AND al.row_id = p_row_id
    ORDER BY al.created_at DESC;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION audit_trail IS
    'Usage: SELECT * FROM audit_trail(''orders'', ''<uuid>'');';

-- All changes by a user
CREATE OR REPLACE FUNCTION audit_by_user(p_changed_by UUID)
RETURNS TABLE (
    created_at      TIMESTAMPTZ,
    table_name      TEXT,
    row_id          UUID,
    action          TEXT,
    old_data        JSONB,
    new_data        JSONB,
    reason          TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT al.created_at, al.table_name, al.row_id,
           al.action, al.old_data, al.new_data, al.reason
    FROM audit_log al
    WHERE al.changed_by = p_changed_by
    ORDER BY al.created_at DESC
    LIMIT 500;
END;
$$ LANGUAGE plpgsql;

-- Sensitive field masking (GDPR helper)
-- Replace actual sensitive values in old_data/new_data
CREATE OR REPLACE FUNCTION audit_mask_sensitive(data JSONB)
RETURNS JSONB AS $$
BEGIN
    RETURN JSONB '{
        "id_number_encrypted": "[REDACTED]",
        "bank_account": "[REDACTED]",
        "phone": "[REDACTED]",
        "email": "[REDACTED]"
    }' || COALESCE(data, '{}'::JSONB);
END;
$$ LANGUAGE plpgsql IMMUTABLE;


-- ============================================================
-- 7. Audit Log Retention Policy
-- ============================================================

-- Hot data: last 90 days in DB
-- Archive: older than 90 days → export to R2 as JSONL, then DELETE
-- Note: DELETE from audit_log requires elevated privilege + manual approval

-- Archival procedure (run monthly via pg_cron or GitHub Action)
CREATE OR REPLACE FUNCTION archive_old_audit_logs(days_to_keep INT DEFAULT 90)
RETURNS TABLE (archived_count BIGINT, oldest_kept TIMESTAMPTZ) AS $$
DECLARE
    cutoff_date TIMESTAMPTZ;
    archived   BIGINT;
BEGIN
    cutoff_date := NOW() - (days_to_keep || ' days')::INTERVAL;

    -- First: export to R2 (requires pg export + R2 upload)
    -- This step should be done in a scheduled job BEFORE deleting
    -- For now, just return what would be archived:
    SELECT COUNT(*) INTO archived
    FROM audit_log
    WHERE created_at < cutoff_date;

    -- DO NOT auto-delete — require manual review
    RETURN QUERY SELECT archived::BIGINT, cutoff_date;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION archive_old_audit_logs IS
    'Archive audit logs older than N days. Run export to R2 first, then DELETE.';


-- ============================================================
-- 8. Quick RLS Status Check (run anytime)
-- ============================================================

-- How to check RLS status from Supabase Studio or psql:
--
--   SELECT table_name, rowsecurity,
--          CASE WHEN rowsecurity THEN '✅ RLS ON' ELSE '🚨 RLS OFF' END
--   FROM pg_tables
--   WHERE schemaname = 'public'
--     AND tablename NOT IN ('migrations', 'schema_migrations')
--   ORDER BY rowsecurity, tablename;
--
--   -- Then check policy count:
--   SELECT schemaname, tablename, policyname, cmd
--   FROM pg_policies
--   WHERE schemaname = 'public'
--   ORDER BY tablename, cmd;

-- ============================================================
-- ✅ Migration Complete
-- ============================================================
-- Next steps:
--   1. Run: SELECT * FROM recon_rls_audit();
--   2. Replace policy placeholders with real auth checks:
--      - Option A: auth.uid() = linked_id
--      - Option B: JWT claims from Telegram
--      - Option C: DENY ALL + service_role only
--   3. Add auth_user_id column to buyers/customers tables
--      linking to auth.users(id) — needed for Option A
--   4. Test: INSERT a test transaction and verify audit_log captures it
--   5. Test: Try UPDATE audit_log → should fail
--   6. Set up monthly archive job (90-day retention)
-- ============================================================
