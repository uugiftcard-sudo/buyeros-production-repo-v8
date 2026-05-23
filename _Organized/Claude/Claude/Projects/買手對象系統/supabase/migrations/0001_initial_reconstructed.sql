-- ============================================================
-- BuyerOS Schema — RECONSTRUCTED FROM AUDIT CLUES
-- ============================================================
-- Status: RECONSTRUCTED — ⚠️  需要用戶在 Supabase Studio 確認
-- Generated: 2026-05-23
-- Project Ref: jnzdklfjdjmhjrhntljp
--
-- HOW TO VERIFY / REPLACE WITH REAL DUMP:
--   1. Run recon/supabase-audit.sql in Supabase Studio SQL Editor
--   2. Download all 12 result CSVs
--   3. Replace this file with: npx supabase db dump --schema public
--   4. Then replace with the actual verified version
--
-- This file serves as a PLACEHOLDER + documentation of expected schema.
-- ============================================================


-- ============================================================
-- A. KNOWN TABLES (from audit clues in backup-system/README.md
--   and GAP-REPORT.md — confirmed to exist in DB)
-- ============================================================

-- buyers              — 買手主表（已在 GAP-REPORT 確認）
-- transactions        — 交易記錄（已確認）
-- refunds             — 退款記錄（已確認）
-- invoices            — 發票（推斷，見 GAP-REPORT C3）
-- buyer_documents     — 買手 KYC 文件（推斷）
-- audit_log           — ⚠️ 未確認是否存在，強烈建議新增


-- ============================================================
-- B. RECONSTRUCTED SCHEMA (estimated from business domain)
-- ============================================================

-- TIER 1: Core Entity Tables (HIGH CONFIDENCE — business requires these)

-- Buyer (買手)
CREATE TABLE IF NOT EXISTS buyers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- identity
    telegram_user_id BIGINT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    phone TEXT,
    -- KYC
    id_type TEXT CHECK (id_type IN ('hkid', 'passport', 'other')),
    id_number_encrypted TEXT, -- 加密儲存
    id_front_url TEXT,        -- storage path
    id_back_url TEXT,
    -- bank
    bank_name TEXT,
    bank_account TEXT,        -- 加密
    bank_account_holder TEXT,
    -- status
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'suspended', 'inactive')),
    -- rating
    rating_avg NUMERIC(3,2) DEFAULT 0,
    rating_count INT DEFAULT 0,
    commission_rate NUMERIC(5,4) DEFAULT 0.05, -- e.g. 0.0500 = 5%, used for settlement calculations
    -- source
    referred_by UUID REFERENCES buyers(id),
    notes TEXT
);

-- Customer (客戶 — distinct from buyers)
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    telegram_user_id BIGINT UNIQUE,
    display_name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
    notes TEXT
);


-- TIER 2: Order / Transaction Flow (HIGH CONFIDENCE)

-- Order (訂單)
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    order_number TEXT UNIQUE NOT NULL, -- human-readable e.g. "ORD-2026-001234"
    customer_id UUID REFERENCES customers(id),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
        'pending', 'assigned', 'in_procurement', 'received', 'delivered', 'completed', 'cancelled'
    )),
    -- procurement
    assigned_buyer_id UUID REFERENCES buyers(id),
    assigned_at TIMESTAMPTZ,
    -- amounts (in HKD cents to avoid floating point)
    total_amount_cents INT NOT NULL,
    deposit_paid_cents INT DEFAULT 0,
    balance_due_cents INT DEFAULT 0,
    -- delivery
    delivery_address TEXT,
    delivery_fee_cents INT DEFAULT 0,
    delivered_at TIMESTAMPTZ,
    delivery_proof_url TEXT, -- photo in storage
    -- metadata
    notes TEXT,
    source_channel TEXT DEFAULT 'telegram' -- telegram / web / admin
);

-- Order Item (訂單明細)
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    product_name TEXT NOT NULL,
    product_url TEXT,           -- link to source product
    quantity INT NOT NULL DEFAULT 1,
    unit_price_cents INT NOT NULL,
    subtotal_cents INT GENERATED ALWAYS AS (quantity * unit_price_cents) STORED,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'procured', 'unavailable', 'refunded')),
    notes TEXT
);


-- TIER 3: Financial Core (HIGH CONFIDENCE)

-- Transaction (收款記錄 — 業務層)
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    transaction_number TEXT UNIQUE NOT NULL,
    order_id UUID REFERENCES orders(id),
    customer_id UUID REFERENCES customers(id),
    type TEXT NOT NULL CHECK (type IN ('payment', 'refund', 'deposit', 'balance', 'commission')),
    -- amounts
    amount_cents INT NOT NULL,
    currency TEXT DEFAULT 'HKD',
    -- payment method
    payment_method TEXT CHECK (payment_method IN ('bank_transfer', 'fps', 'cash', 'other')),
    payment_reference TEXT, -- bank ref / FPS ID
    paid_at TIMESTAMPTZ,
    -- status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'failed', 'reversed')),
    -- Telegram message ref
    tg_message_id BIGINT,
    notes TEXT
);

-- Refund (退款)
CREATE TABLE IF NOT EXISTS refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    refund_number TEXT UNIQUE NOT NULL,
    transaction_id UUID NOT NULL REFERENCES transactions(id),
    order_id UUID REFERENCES orders(id),
    customer_id UUID REFERENCES customers(id),
    amount_cents INT NOT NULL,
    reason TEXT,
    reason_detail TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'processing', 'completed', 'rejected')),
    approved_by UUID, -- buyer or admin who approved
    approved_at TIMESTAMPTZ,
    processed_at TIMESTAMPTZ,
    -- journal entry linkage (see Tier 4)
    journal_entry_id UUID, -- TODO: add foreign key after journal_entries exists
    notes TEXT
);

-- Settlement (結算 — 買手分潤)
CREATE TABLE IF NOT EXISTS settlements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    settlement_number TEXT UNIQUE NOT NULL,
    buyer_id UUID NOT NULL REFERENCES buyers(id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_orders INT NOT NULL DEFAULT 0,
    total_sales_cents INT NOT NULL DEFAULT 0,
    commission_rate NUMERIC(5,4) NOT NULL, -- e.g. 0.0500 = 5%
    commission_amount_cents INT NOT NULL DEFAULT 0,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'paid', 'disputed')),
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    payment_reference TEXT,
    notes TEXT
);


-- TIER 4: Accounting Layer (MEDIUM CONFIDENCE — may not exist yet)

-- Chart of Accounts (會計科目表)
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_code TEXT UNIQUE NOT NULL, -- e.g. "1100", "2100", "4100"
    account_name TEXT NOT NULL,
    account_name_en TEXT,
    type TEXT NOT NULL CHECK (type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
    subtype TEXT, -- bank / cash / ar / ap / etc.
    parent_id UUID REFERENCES accounts(id),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT
);

-- Journal Entry (複式記賬)
CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_number TEXT UNIQUE NOT NULL,
    entry_date DATE NOT NULL,
    period_id UUID, -- accounting_periods.id
    source_type TEXT NOT NULL CHECK (source_type IN ('transaction', 'refund', 'settlement', 'manual', 'invoice', 'receipt')),
    source_id UUID, -- link to source record (e.g. transactions.id)
    memo TEXT,
    posted_at TIMESTAMPTZ DEFAULT NOW(),
    posted_by UUID, -- auth.users.id
    is_reversed BOOLEAN DEFAULT FALSE,
    reversed_by UUID REFERENCES journal_entries(id),
    notes TEXT
);

-- Journal Line (分錄行)
CREATE TABLE IF NOT EXISTS journal_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    account_id UUID NOT NULL REFERENCES accounts(id),
    debit_cents INT DEFAULT 0 CHECK (debit_cents >= 0),
    credit_cents INT DEFAULT 0 CHECK (credit_cents >= 0),
    CHECK (debit_cents = 0 OR credit_cents = 0), -- either debit OR credit, not both
    memo TEXT
);

-- Accounting Period (會計期間)
CREATE TABLE IF NOT EXISTS accounting_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period TEXT UNIQUE NOT NULL, -- e.g. "2026-05" (matching the frontend's period field)
    period_name TEXT, -- friendly name e.g. "May 2026"
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT DEFAULT 'open' CHECK (status IN ('open', 'closed', 'archived')),
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    opened_by TEXT,
    closed_by TEXT,
    notes TEXT
);


-- TIER 5: Documents / Storage

-- Documents (文件存儲記錄)
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ref_type TEXT NOT NULL CHECK (ref_type IN ('order', 'buyer', 'customer', 'refund', 'settlement', 'invoice', 'receipt')),
    ref_id UUID NOT NULL,
    storage_path TEXT NOT NULL, -- e.g. "receipts/2026/05/ord-123.png"
    file_name TEXT NOT NULL,
    file_size_bytes BIGINT,
    mime_type TEXT,
    uploaded_by UUID,
    description TEXT
);

-- Invoice (發票)
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    invoice_number TEXT UNIQUE NOT NULL,
    customer_id UUID REFERENCES customers(id),
    order_id UUID REFERENCES orders(id),
    amount_cents INT NOT NULL,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'issued', 'paid', 'cancelled', 'void')),
    issued_at TIMESTAMPTZ,
    due_date DATE,
    paid_at TIMESTAMPTZ,
    pdf_storage_path TEXT,
    notes TEXT
);


-- TIER 6: Audit & System

-- Audit Log (審計日誌)
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    table_name TEXT NOT NULL,
    row_id UUID NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data JSONB,
    new_data JSONB,
    changed_by UUID, -- auth.users.id
    changed_by_role TEXT, -- 'admin', 'buyer', 'customer', 'system'
    ip_address INET,
    tg_message_id BIGINT,
    reason TEXT
);


-- ============================================================
-- C. INDEXES (performance)
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_buyer ON orders(assigned_buyer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_order ON transactions(order_id);
CREATE INDEX IF NOT EXISTS idx_transactions_customer ON transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_refunds_transaction ON refunds(transaction_id);
CREATE INDEX IF NOT EXISTS idx_refunds_order ON refunds(order_id);
CREATE INDEX IF NOT EXISTS idx_refunds_status ON refunds(status);
CREATE INDEX IF NOT EXISTS idx_settlements_buyer ON settlements(buyer_id);
CREATE INDEX IF NOT EXISTS idx_settlements_period ON settlements(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_journal_entries_date ON journal_entries(entry_date);
CREATE INDEX IF NOT EXISTS idx_journal_entries_source ON journal_entries(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_entry ON journal_lines(entry_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_table_row ON audit_log(table_name, row_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC);


-- ============================================================
-- D. UPDATED_AT TRIGGER FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables with updated_at
CREATE TRIGGER trg_buyers_updated_at BEFORE UPDATE ON buyers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_customers_updated_at BEFORE UPDATE ON customers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_orders_updated_at BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_refunds_updated_at BEFORE UPDATE ON refunds
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ============================================================
-- E. RLS POLICIES (must be reviewed and applied)
-- ============================================================

-- Enable RLS on all user-facing tables
ALTER TABLE buyers ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE refunds ENABLE ROW LEVEL SECURITY;
ALTER TABLE settlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_lines ENABLE ROW LEVEL SECURITY;

-- Example RLS policies (⚠️ 需要根據實際 auth 方式調整)
-- Supabase Auth user:
--   admin sees all
--   buyer sees own data (buyer_id = auth.uid())
--   customer sees own data (customer_id = auth.uid())

-- BUYERS: buyers see their own row; admins see all
CREATE POLICY "buyers_self_read" ON buyers FOR SELECT
    USING (telegram_user_id = NULL); -- placeholder: auth.uid() check

CREATE POLICY "buyers_admin_all" ON buyers FOR ALL
    USING (TRUE); -- admin role check placeholder

-- ORDERS: buyer sees own assigned orders; customer sees own orders
CREATE POLICY "orders_buyer_read" ON orders FOR SELECT
    USING (assigned_buyer_id = NULL); -- auth.uid() check placeholder

CREATE POLICY "orders_customer_read" ON orders FOR SELECT
    USING (customer_id = NULL); -- auth.uid() check placeholder

CREATE POLICY "orders_admin_all" ON orders FOR ALL
    USING (TRUE);

-- TRANSACTIONS: similar pattern
CREATE POLICY "transactions_buyer_read" ON transactions FOR SELECT
    USING (TRUE); -- placeholder

CREATE POLICY "transactions_admin_all" ON transactions FOR ALL
    USING (TRUE);

-- REFUNDS: admin only write; buyer/customer read own
CREATE POLICY "refunds_read_own" ON refunds FOR SELECT
    USING (TRUE); -- placeholder

CREATE POLICY "refunds_admin_all" ON refunds FOR ALL
    USING (TRUE);

-- AUDIT LOG: admin only
CREATE POLICY "audit_log_admin_only" ON audit_log FOR SELECT
    USING (TRUE);

-- ⚠️ 重要：以上 RLS policy 全部係 PLACEHOLDER
-- 必須根據以下方式之一替換：
--   A. 如果用 Supabase Auth → auth.uid() 對 telegram_user_id / customer UUID
--   B. 如果用 Telegram OAuth → JWT claims 方式
--   C. 如果係 server-side only → 全部 deny 然後透過 Edge Function 訪問
-- 建議用 Option A，結構最清晰


-- ============================================================
-- F. AUDIT TRIGGER (change tracking)
-- ============================================================

-- Generic audit log trigger
CREATE OR REPLACE FUNCTION log_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (table_name, row_id, action, old_data, new_data)
    VALUES (
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        TG_OP,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Apply to critical tables
CREATE TRIGGER trg_buyers_audit
    AFTER INSERT OR UPDATE OR DELETE ON buyers
    FOR EACH ROW EXECUTE FUNCTION log_changes();

CREATE TRIGGER trg_orders_audit
    AFTER INSERT OR UPDATE OR DELETE ON orders
    FOR EACH ROW EXECUTE FUNCTION log_changes();

CREATE TRIGGER trg_transactions_audit
    AFTER INSERT OR UPDATE OR DELETE ON transactions
    FOR EACH ROW EXECUTE FUNCTION log_changes();

CREATE TRIGGER trg_refunds_audit
    AFTER INSERT OR UPDATE OR DELETE ON refunds
    FOR EACH ROW EXECUTE FUNCTION log_changes();


-- ============================================================
-- G. REPORTS VIEWS
-- ============================================================

-- v_trial_balance: 試算表
CREATE OR REPLACE VIEW v_trial_balance AS
SELECT
    a.account_code,
    a.account_name,
    a.type,
    SUM(jl.debit_cents) AS total_debit_cents,
    SUM(jl.credit_cents) AS total_credit_cents,
    CASE a.type
        WHEN 'asset'     THEN SUM(jl.debit_cents) - SUM(jl.credit_cents)
        WHEN 'expense'  THEN SUM(jl.debit_cents) - SUM(jl.credit_cents)
        WHEN 'liability' THEN SUM(jl.credit_cents) - SUM(jl.debit_cents)
        WHEN 'equity'    THEN SUM(jl.credit_cents) - SUM(jl.debit_cents)
        WHEN 'revenue'   THEN SUM(jl.credit_cents) - SUM(jl.debit_cents)
    END AS balance_cents
FROM accounts a
LEFT JOIN journal_lines jl ON jl.account_id = a.id
GROUP BY a.id, a.account_code, a.account_name, a.type;

-- v_monthly_pnl: 月度損益
CREATE OR REPLACE VIEW v_monthly_pnl AS
SELECT
    TO_CHAR(je.entry_date, 'YYYY-MM') AS month,
    a.type,
    a.account_name,
    SUM(jl.debit_cents) AS debit_cents,
    SUM(jl.credit_cents) AS credit_cents,
    CASE
        WHEN a.type IN ('expense') THEN SUM(jl.debit_cents)
        WHEN a.type IN ('revenue') THEN SUM(jl.credit_cents)
    END AS amount_cents
FROM journal_entries je
JOIN journal_lines jl ON jl.entry_id = je.id
JOIN accounts a ON a.id = jl.account_id
WHERE a.type IN ('revenue', 'expense')
GROUP BY TO_CHAR(je.entry_date, 'YYYY-MM'), a.type, a.account_name
ORDER BY month DESC, a.type;


-- ============================================================
-- NEXT STEPS after replacing with real schema dump:
-- ============================================================
-- 1. Replace this file with: npx supabase db dump --schema public
--    (after running: npx supabase login && npx supabase link --project-ref jnzdklfjdjmhjrhntljp)
-- 2. Remove placeholder tables marked with "IF NOT EXISTS" once real schema confirmed
-- 3. Replace RLS policy placeholder conditions with real auth checks
-- 4. Run recon/supabase-audit.sql to verify schema match
-- 5. Update this file's header to mark as "VERIFIED"
-- ============================================================
