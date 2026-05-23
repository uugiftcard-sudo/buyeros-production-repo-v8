-- ============================================================
-- P2: 會計層 Schema Migration
-- BuyerOS（買手對象系統）
-- ============================================================
-- Migration: 0002_accounting_layer.sql
-- Depends on: 0001_initial_reconstructed.sql (or real schema)
-- Scope:
--   - Chart of Accounts (COA)
--   - Journal Entries + Journal Lines (雙式記賬)
--   - Accounting Periods + Month-End Close
--   - Financial Views (Trial Balance, P&L, Balance Sheet)
--   - Auto-posting triggers (transaction → journal entry)
--
-- IMPORTANT: This migration adds to the schema — it does NOT
-- replace 0001. Apply 0001 first.
-- ============================================================


-- ============================================================
-- 0. Dependency check
-- ============================================================
DO $$
BEGIN
    -- Verify critical tables exist before adding accounting layer
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'transactions'
    ) THEN
        RAISE EXCEPTION 'Table "transactions" not found. Apply 0001 first.';
    END IF;
END;
$$;


-- ============================================================
-- 1. Chart of Accounts (會計科目表)
-- ============================================================

CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_code TEXT UNIQUE NOT NULL,  -- e.g. "1100", "2100", "4101"
    account_name TEXT NOT NULL,          -- 中文名
    account_name_en TEXT,               -- 英文名
    type TEXT NOT NULL CHECK (
        type IN ('asset', 'liability', 'equity', 'revenue', 'expense')
    ),
    subtype TEXT,  -- bank / cash / ar / ap / commission / refund / etc.
    parent_id UUID REFERENCES accounts(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_cash_flow_relevant BOOLEAN NOT NULL DEFAULT FALSE,
    tax_category TEXT,  -- HK: 空 or "profit-taxable"
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- COA: 5 大類 Account Codes
-- Asset (1xxx): 資產
-- Liability (2xxx): 負債
-- Equity (3xxx): 權益
-- Revenue (4xxx): 收入
-- Expense (5xxx): 支出

COMMENT ON TABLE accounts IS
    'Chart of Accounts — 會計科目表。每一行係一個獨立嘅 account，雙式記賬嘅 debit/credit 都記入呢度。';


-- Seed COA for BuyerOS 代購平台業務
INSERT INTO accounts (account_code, account_name, account_name_en, type, subtype, is_cash_flow_relevant)
VALUES
    -- =============================================
    -- ASSETS (資產)
    -- =============================================
    -- 1100: Cash & Bank
    ('1101', '銀行戶口 — HSBC',        'HSBC Bank Account',        'asset', 'bank', TRUE),
    ('1102', '銀行戶口 — 其他',         'Other Bank Account',        'asset', 'bank', TRUE),
    ('1109', '零用現金',                'Petty Cash',                 'asset', 'cash', TRUE),

    -- 1200: Receivables
    ('1201', '應收帳款 — 客戶',         'Accounts Receivable',        'asset', 'ar',    FALSE),
    ('1202', '應收帳款 — 買手',         'Buyer Receivables',          'asset', 'ar',    FALSE),

    -- 1300: Inventory / Prepayments
    ('1301', '在途貨品',                'Goods in Transit',            'asset', 'inventory', FALSE),
    ('1302', '預付款項',                'Prepayments',                 'asset', 'prepay', FALSE),

    -- =============================================
    -- LIABILITIES (負債)
    -- =============================================
    -- 2100: Payables
    ('2101', '應付帳款 — 供應商',       'Accounts Payable — Supplier','liability', 'ap', FALSE),
    ('2102', '應付帳款 — 買手結算',     'Payable — Buyer Settlement', 'liability', 'ap', FALSE),

    -- 2200: Tax Liabilities
    ('2201', '應繳利得稅',             'Profits Tax Payable',         'liability', 'tax', FALSE),

    -- 2300: Other Liabilities
    ('2301', '暫收款項',               'Suspense Receipts',           'liability', 'suspense', FALSE),

    -- =============================================
    -- EQUITY (權益)
    -- =============================================
    ('3101', '實繳資本',               'Paid-in Capital',             'equity', 'capital', FALSE),
    ('3102', '保留盈利',               'Retained Earnings',           'equity', 'retained', FALSE),
    ('3103', '本期損益',               'Current Year P&L',            'equity', 'pnl', FALSE),

    -- =============================================
    -- REVENUE (收入)
    -- =============================================
    -- 4100: Platform Revenue
    ('4101', '代購服務費收入',         'Procurement Service Revenue', 'revenue', 'commission', FALSE),
    ('4102', '手續費收入',             'Handling Fee Revenue',        'revenue', 'fee', FALSE),

    -- 4200: Other Revenue
    ('4201', '利息收入',               'Interest Income',            'revenue', 'interest', FALSE),

    -- =============================================
    -- EXPENSES (支出)
    -- =============================================
    -- 5100: Cost of Sales
    ('5101', '採購成本',               'Procurement Cost',           'expense', 'cos', FALSE),
    ('5102', '退貨成本',               'Cost of Refunds',            'expense', 'refund_cos', FALSE),

    -- 5200: Operating Expenses
    ('5201', '退款支出',               'Refund Expenses',            'expense', 'refund', FALSE),
    ('5202', '平台運營支出',           'Platform Operating Expenses', 'expense', 'opex', FALSE),

    -- 5300: Finance Costs
    ('5301', '銀行費用',               'Bank Charges',               'expense', 'bank_fee', FALSE),

    -- 5400: Tax Expenses
    ('5401', '利得稅支出',             'Profits Tax Expense',        'expense', 'tax', FALSE)
ON CONFLICT (account_code) DO NOTHING;


-- ============================================================
-- 2. Accounting Periods (會計期間)
-- ============================================================

CREATE TABLE IF NOT EXISTS accounting_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_name TEXT UNIQUE NOT NULL,  -- "2026-05"
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'closed', 'archived')),
    closed_at TIMESTAMPTZ,
    closed_by UUID,  -- auth.users.id
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE accounting_periods IS
    '會計期間。Month-end close 之後 lock 期間，journal entry 唔可以再改。';

-- Seed current and next 12 periods
DO $$
DECLARE
    p_start DATE;
    p_end   DATE;
    p_name  TEXT;
    i       INT;
BEGIN
    FOR i IN 0..12 LOOP
        p_start := DATE_TRUNC('month', CURRENT_DATE) + (i || ' months')::INTERVAL;
        p_end   := p_start + '1 month - 1 day'::INTERVAL;
        p_name  := TO_CHAR(p_start, 'YYYY-MM');

        INSERT INTO accounting_periods (period_name, start_date, end_date, status)
        VALUES (p_name, p_start, p_end, CASE WHEN i = 0 THEN 'open' ELSE 'open' END)
        ON CONFLICT (period_name) DO NOTHING;
    END LOOP;
END;
$$;


-- ============================================================
-- 3. Journal Entries (日記帳)
-- ============================================================

CREATE TABLE IF NOT EXISTS journal_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_number TEXT UNIQUE NOT NULL,  -- "JE-2026-05-0001"
    entry_date DATE NOT NULL,
    period_id UUID REFERENCES accounting_periods(id),

    -- Source tracking (link to business event)
    source_type TEXT NOT NULL CHECK (
        source_type IN (
            'transaction', 'refund', 'settlement',
            'invoice', 'manual', 'reversal', 'opening'
        )
    ),
    source_id UUID,  -- transactions.id / refunds.id / etc.
    source_ref TEXT,  -- human-readable ref e.g. "ORD-2026-0001"

    -- Content
    memo TEXT NOT NULL,
    is_reversal BOOLEAN NOT NULL DEFAULT FALSE,
    reversed_by UUID REFERENCES journal_entries(id),

    -- Audit
    posted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    posted_by UUID,  -- auth.users.id or 'system'::text
    posted_by_role TEXT CHECK (posted_by_role IN ('admin', 'buyer', 'customer', 'system')),

    -- Immutable: no updated_at — entries should not change after posting
    CONSTRAINT no_date_before_company_start CHECK (
        entry_date >= DATE '2024-01-01'
    )
);

COMMENT ON TABLE journal_entries IS
    '日記帳 Header — 每個業務事件（收款、退款、結算）會自動或手動產生一行 journal entry。';

-- Auto-update accounting_period reference
CREATE OR REPLACE FUNCTION derive_period_from_date()
RETURNS TRIGGER AS $$
DECLARE
    derived_period_id UUID;
BEGIN
    SELECT id INTO derived_period_id
    FROM accounting_periods
    WHERE NEW.entry_date BETWEEN start_date AND end_date
    LIMIT 1;

    NEW.period_id := derived_period_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_journal_entry_derive_period
    BEFORE INSERT ON journal_entries
    FOR EACH ROW
    EXECUTE FUNCTION derive_period_from_date();

-- Entry number generator
CREATE OR REPLACE FUNCTION next_entry_number(p_date DATE)
RETURNS TEXT AS $$
DECLARE
    seq INT;
    date_part TEXT;
BEGIN
    date_part := TO_CHAR(p_date, 'YYYY-MM');

    SELECT COALESCE(MAX(
        CAST(SUBSTRING(entry_number FROM 'JE-' || date_part || '-(\d{4})') AS INT)
    ), 0) + 1 INTO seq
    FROM journal_entries
    WHERE entry_number LIKE 'JE-' || date_part || '-%';

    RETURN 'JE-' || date_part || '-' || LPAD(seq::TEXT, 4, '0');
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 4. Journal Lines (分錄行)
-- ============================================================

CREATE TABLE IF NOT EXISTS journal_lines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_id UUID NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,

    account_id UUID NOT NULL REFERENCES accounts(id),

    -- Cents to avoid floating point; 0 = not applicable
    debit_cents INT NOT NULL DEFAULT 0 CHECK (debit_cents >= 0),
    credit_cents INT NOT NULL DEFAULT 0 CHECK (credit_cents >= 0),

    -- Either debit OR credit — not both
    CONSTRAINT chk_debit_or_credit CHECK (
        (debit_cents > 0 AND credit_cents = 0) OR
        (credit_cents > 0 AND debit_cents = 0)
    ),

    memo TEXT
);

COMMENT ON TABLE journal_lines IS
    '分錄行 — 一個 journal entry 有 2+ 行。每一行 debit 或 credit 一個 account。';

-- Auto-enforce double-entry balance per entry
CREATE OR REPLACE FUNCTION enforce_entry_balance()
RETURNS TRIGGER AS $$
DECLARE
    entry_debit  INT;
    entry_credit INT;
BEGIN
    SELECT
        COALESCE(SUM(debit_cents),  0),
        COALESCE(SUM(credit_cents), 0)
    INTO entry_debit, entry_credit
    FROM journal_lines
    WHERE entry_id = NEW.entry_id;

    IF entry_debit != entry_credit THEN
        RAISE EXCEPTION 'Journal entry is not balanced: debit=%, credit=%. Sum must be equal.',
            entry_debit, entry_credit
            USING HINT = 'Every journal entry must have equal debit and credit totals.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_enforce_entry_balance
    AFTER INSERT OR UPDATE OR DELETE ON journal_lines
    FOR EACH ROW
    EXECUTE FUNCTION enforce_entry_balance();


-- ============================================================
-- 5. Period-Lock: Closed periods cannot be modified
-- ============================================================

CREATE OR REPLACE FUNCTION lock_period_journal_lines()
RETURNS TRIGGER AS $$
DECLARE
    line_entry_date    DATE;
    line_entry_period  TEXT;
BEGIN
    SELECT je.entry_date INTO line_entry_date
    FROM journal_entries je
    WHERE je.id = NEW.entry_id;

    SELECT ap.status INTO line_entry_period
    FROM accounting_periods ap
    WHERE ap.start_date <= line_entry_date
      AND ap.end_date >= line_entry_date;

    IF line_entry_period = 'closed' THEN
        RAISE EXCEPTION 'Cannot modify journal lines in a closed period (%)', line_entry_period
        USING HINT = 'Reopen the period first: UPDATE accounting_periods SET status=''open'' WHERE ...';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lock_closed_period
    BEFORE INSERT OR UPDATE OR DELETE ON journal_lines
    FOR EACH ROW
    EXECUTE FUNCTION lock_period_journal_lines();

-- Same for journal_entries
CREATE OR REPLACE FUNCTION lock_period_journal_entries()
RETURNS TRIGGER AS $$
DECLARE
    p_status TEXT;
BEGIN
    SELECT status INTO p_status
    FROM accounting_periods
    WHERE NEW.period_id = id;

    IF p_status = 'closed' THEN
        RAISE EXCEPTION 'Cannot modify journal entries in closed period.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_lock_closed_journal_entries
    BEFORE UPDATE OR DELETE ON journal_entries
    FOR EACH ROW
    EXECUTE FUNCTION lock_period_journal_entries();


-- ============================================================
-- 6. Auto-Posting: Business Event → Journal Entry
-- ============================================================
-- 每個業務事件自動產生 journal entry。
-- Trigger 掛在 transactions / refunds / settlements 表上。

-- 6a. Auto-post from TRANSACTION
CREATE OR REPLACE FUNCTION post_transaction_journal()
RETURNS TRIGGER AS $$
DECLARE
    entry_id     UUID;
    acc_cash     UUID;
    acc_ar       UUID;
    acc_rev      UUID;
    acc_fee      UUID;
BEGIN
    -- Cash account (for HKD payments)
    SELECT id INTO acc_cash
    FROM accounts WHERE account_code = '1101';

    -- AR account
    SELECT id INTO acc_ar
    FROM accounts WHERE account_code = '1201';

    -- Revenue accounts
    SELECT id INTO acc_rev
    FROM accounts WHERE account_code = '4101';

    SELECT id INTO acc_fee
    FROM accounts WHERE account_code = '4102';

    -- Create journal entry
    INSERT INTO journal_entries (
        entry_number, entry_date, source_type, source_id, source_ref, memo,
        posted_by, posted_by_role
    ) VALUES (
        next_entry_number(COALESCE(NEW.paid_at::DATE, NEW.created_at::DATE)),
        COALESCE(NEW.paid_at::DATE, NEW.created_at::DATE),
        'transaction',
        NEW.id,
        NEW.transaction_number,
        CASE NEW.type
            WHEN 'payment'   THEN 'Customer payment received: ' || COALESCE(NEW.transaction_number, NEW.id::TEXT)
            WHEN 'deposit'   THEN 'Deposit received: '          || COALESCE(NEW.transaction_number, NEW.id::TEXT)
            WHEN 'balance'    THEN 'Balance payment received: ' || COALESCE(NEW.transaction_number, NEW.id::TEXT)
            WHEN 'commission' THEN 'Commission received: '      || COALESCE(NEW.transaction_number, NEW.id::TEXT)
            ELSE 'Transaction: ' || COALESCE(NEW.transaction_number, NEW.id::TEXT)
        END,
        'system', 'system'
    ) RETURNING id INTO entry_id;

    IF NEW.type IN ('payment', 'deposit', 'balance') THEN
        -- DEBIT: Cash / Bank
        INSERT INTO journal_lines (entry_id, account_id, debit_cents, memo)
        VALUES (entry_id, acc_cash, NEW.amount_cents,
            'Received from customer: ' || COALESCE(NEW.transaction_number, ''));

        -- CREDIT: Revenue
        INSERT INTO journal_lines (entry_id, account_id, credit_cents, memo)
        VALUES (entry_id, acc_rev, NEW.amount_cents,
            'Procurement service revenue: ' || COALESCE(NEW.transaction_number, ''));

    ELSIF NEW.type = 'commission' THEN
        -- DEBIT: Cash
        INSERT INTO journal_lines (entry_id, account_id, debit_cents, memo)
        VALUES (entry_id, acc_cash, NEW.amount_cents,
            'Commission received: ' || COALESCE(NEW.transaction_number, ''));

        -- CREDIT: Fee revenue
        INSERT INTO journal_lines (entry_id, account_id, credit_cents, memo)
        VALUES (entry_id, acc_fee, NEW.amount_cents,
            'Handling fee: ' || COALESCE(NEW.transaction_number, ''));
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: Only apply AFTER verifying transactions table has a `type` column
-- with values: payment, deposit, balance, commission, refund
-- If the actual enum is different, update the CASE above.

-- 6b. Auto-post from REFUND
CREATE OR REPLACE FUNCTION post_refund_journal()
RETURNS TRIGGER AS $$
DECLARE
    entry_id   UUID;
    acc_cash   UUID;
    acc_ar     UUID;
    acc_exp    UUID;
    acc_rev    UUID;
BEGIN
    SELECT id INTO acc_cash FROM accounts WHERE account_code = '1101';
    SELECT id INTO acc_ar   FROM accounts WHERE account_code = '1201';
    SELECT id INTO acc_exp  FROM accounts WHERE account_code = '5201';
    SELECT id INTO acc_rev  FROM accounts WHERE account_code = '4101';

    -- Only post when refund is approved/processed
    IF NEW.status IN ('approved', 'processing', 'completed')
       AND OLD.status IN ('pending', 'rejected') THEN

        INSERT INTO journal_entries (
            entry_number, entry_date, source_type, source_id, source_ref, memo,
            posted_by, posted_by_role
        ) VALUES (
            next_entry_number(COALESCE(NEW.processed_at::DATE, NEW.updated_at::DATE)),
            COALESCE(NEW.processed_at::DATE, NEW.updated_at::DATE),
            'refund',
            NEW.id,
            NEW.refund_number,
            'Refund processed: ' || COALESCE(NEW.refund_number, NEW.id::TEXT) ||
            ' — ' || COALESCE(NEW.reason, ''),
            'system', 'system'
        ) RETURNING id INTO entry_id;

        -- DEBIT: Refund Expense
        INSERT INTO journal_lines (entry_id, account_id, debit_cents, memo)
        VALUES (entry_id, acc_exp, NEW.amount_cents,
            'Refund issued: ' || COALESCE(NEW.refund_number, ''));

        -- CREDIT: Cash / Bank
        INSERT INTO journal_lines (entry_id, account_id, credit_cents, memo)
        VALUES (entry_id, acc_cash, NEW.amount_cents,
            'Refund paid out: ' || COALESCE(NEW.refund_number, ''));

        -- Also reverse the original revenue (if linked)
        IF NEW.transaction_id IS NOT NULL THEN
            INSERT INTO journal_lines (entry_id, account_id, debit_cents, memo)
            VALUES (entry_id, acc_rev, NEW.amount_cents,
                'Revenue reversal (refund): ' || COALESCE(NEW.refund_number, ''));
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Note: Only apply AFTER verifying refunds table has status column.
-- Only fires on UPDATE from pending → approved/processing/completed.


-- ============================================================
-- 7. Month-End Close Stored Procedure
-- ============================================================

CREATE OR REPLACE FUNCTION close_accounting_period(p_period_name TEXT)
RETURNS VOID AS $$
DECLARE
    period_rec RECORD;
    retained   UUID;
    current_pnl UUID;
    total_revenue INT;
    total_expense INT;
BEGIN
    -- Verify period is open
    SELECT * INTO period_rec
    FROM accounting_periods
    WHERE period_name = p_period_name AND status = 'open';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Period "%" not found or already closed.', p_period_name;
    END IF;

    -- Get Retained Earnings account
    SELECT id INTO retained FROM accounts WHERE account_code = '3102';
    SELECT id INTO current_pnl FROM accounts WHERE account_code = '3103';

    -- Calculate P&L for period
    SELECT
        COALESCE(SUM(jl.credit_cents), 0) INTO total_revenue
    FROM journal_lines jl
    JOIN journal_entries je ON je.id = jl.entry_id
    JOIN accounts a ON a.id = jl.account_id
    WHERE a.type = 'revenue'
      AND je.entry_date BETWEEN period_rec.start_date AND period_rec.end_date;

    SELECT
        COALESCE(SUM(jl.debit_cents), 0) INTO total_expense
    FROM journal_lines jl
    JOIN journal_entries je ON je.id = jl.entry_id
    JOIN accounts a ON a.id = jl.account_id
    WHERE a.type = 'expense'
      AND je.entry_date BETWEEN period_rec.start_date AND period_rec.end_date;

    -- Post closing entry: Revenue → P&L account
    IF total_revenue > 0 THEN
        INSERT INTO journal_entries (
            entry_number, entry_date, source_type, memo, posted_by, posted_by_role
        ) VALUES (
            next_entry_number(period_rec.end_date),
            period_rec.end_date,
            'manual',
            'Month-end close: transfer revenue to P&L (' || p_period_name || ')',
            'system', 'system'
        );

        INSERT INTO journal_lines (entry_id, account_id, debit_cents, memo)
        SELECT currval('journal_entries_id_seq'), id, total_revenue,
               'Close revenue account: ' || account_name
        FROM accounts WHERE account_code = '4101';

        INSERT INTO journal_lines (entry_id, account_id, credit_cents, memo)
        SELECT currval('journal_entries_id_seq'), id, total_revenue,
               'Transfer to P&L: ' || account_name
        FROM accounts WHERE account_code = '3103';
    END IF;

    -- Close the period
    UPDATE accounting_periods
    SET status = 'closed', closed_at = NOW()
    WHERE id = period_rec.id;

    RAISE NOTICE 'Period "%" closed. Revenue=%, Expense=%, Net=% cents.',
        p_period_name, total_revenue, total_expense,
        total_revenue - total_expense;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- 8. Report Views
-- ============================================================

-- 8a. Trial Balance (試算表)
CREATE OR REPLACE VIEW v_trial_balance AS
SELECT
    a.account_code,
    a.account_name,
    a.type,
    a.subtype,
    COALESCE(SUM(jl.debit_cents),  0) AS total_debit_cents,
    COALESCE(SUM(jl.credit_cents), 0) AS total_credit_cents,
    CASE a.type
        WHEN 'asset'     THEN COALESCE(SUM(jl.debit_cents), 0)  - COALESCE(SUM(jl.credit_cents), 0)
        WHEN 'expense'   THEN COALESCE(SUM(jl.debit_cents), 0)  - COALESCE(SUM(jl.credit_cents), 0)
        WHEN 'liability' THEN COALESCE(SUM(jl.credit_cents), 0) - COALESCE(SUM(jl.debit_cents), 0)
        WHEN 'equity'    THEN COALESCE(SUM(jl.credit_cents), 0) - COALESCE(SUM(jl.debit_cents), 0)
        WHEN 'revenue'   THEN COALESCE(SUM(jl.credit_cents), 0) - COALESCE(SUM(jl.debit_cents), 0)
    END AS balance_cents
FROM accounts a
LEFT JOIN journal_lines jl ON jl.account_id = a.id
LEFT JOIN journal_entries je ON je.id = jl.entry_id
GROUP BY a.id, a.account_code, a.account_name, a.type, a.subtype
HAVING
    COALESCE(SUM(jl.debit_cents), 0) > 0
    OR COALESCE(SUM(jl.credit_cents), 0) > 0
    OR a.type IN ('asset', 'liability', 'equity')  -- always show BS accounts
ORDER BY a.account_code;

-- 8b. Profit & Loss by Month (月報損益表)
CREATE OR REPLACE VIEW v_monthly_pnl AS
SELECT
    TO_CHAR(je.entry_date, 'YYYY-MM')       AS period,
    a.type                                   AS category,
    a.account_code,
    a.account_name,
    COALESCE(SUM(jl.debit_cents),  0)       AS debit_cents,
    COALESCE(SUM(jl.credit_cents), 0)       AS credit_cents,
    CASE a.type
        WHEN 'expense' THEN COALESCE(SUM(jl.debit_cents), 0)
        WHEN 'revenue' THEN COALESCE(SUM(jl.credit_cents), 0)
    END                                     AS amount_cents
FROM journal_entries je
JOIN journal_lines jl  ON jl.entry_id = je.id
JOIN accounts a       ON a.id = jl.account_id
WHERE a.type IN ('revenue', 'expense')
GROUP BY TO_CHAR(je.entry_date, 'YYYY-MM'), a.type, a.account_code, a.account_name
ORDER BY period DESC, a.type, a.account_code;

-- 8c. P&L Summary (月度 P&L 摘要)
CREATE OR REPLACE VIEW v_pnl_summary AS
SELECT
    TO_CHAR(je.entry_date, 'YYYY-MM')  AS period,
    'Revenue'                            AS label,
    SUM(jl.credit_cents)                 AS amount_cents,
    1                                    AS sort_order
FROM journal_entries je
JOIN journal_lines jl ON jl.entry_id = je.id
JOIN accounts a ON a.id = jl.account_id
WHERE a.type = 'revenue'
GROUP BY TO_CHAR(je.entry_date, 'YYYY-MM')
UNION ALL
SELECT
    TO_CHAR(je.entry_date, 'YYYY-MM'),
    'Expenses',
    SUM(jl.debit_cents),
    2
FROM journal_entries je
JOIN journal_lines jl ON jl.entry_id = je.id
JOIN accounts a ON a.id = jl.account_id
WHERE a.type = 'expense'
GROUP BY TO_CHAR(je.entry_date, 'YYYY-MM')
UNION ALL
SELECT
    TO_CHAR(je.entry_date, 'YYYY-MM'),
    'Net Profit',
    SUM(jl.credit_cents) - SUM(jl.debit_cents),
    3
FROM journal_entries je
JOIN journal_lines jl ON jl.entry_id = je.id
JOIN accounts a ON a.id = jl.account_id
WHERE a.type IN ('revenue', 'expense')
GROUP BY TO_CHAR(je.entry_date, 'YYYY-MM')
ORDER BY period DESC, sort_order;

-- 8d. Balance Sheet (資產負債表) at a point in time
-- Usage: SELECT * FROM v_balance_sheet('2026-05-31');
CREATE OR REPLACE FUNCTION v_balance_sheet(as_of_date DATE)
RETURNS TABLE (
    account_code    TEXT,
    account_name    TEXT,
    type            TEXT,
    amount_cents    BIGINT,
    section         TEXT
) AS $$
BEGIN
    RETURN QUERY
    -- ASSETS
    SELECT
        a.account_code,
        a.account_name,
        a.type,
        (COALESCE(SUM(jl.debit_cents), 0) - COALESCE(SUM(jl.credit_cents), 0))::BIGINT,
        'ASSETS'::TEXT
    FROM accounts a
    LEFT JOIN journal_lines jl ON jl.account_id = a.id
    LEFT JOIN journal_entries je ON je.id = jl.entry_id
    WHERE a.type = 'asset'
      AND (je.entry_date IS NULL OR je.entry_date <= as_of_date)
    GROUP BY a.id, a.account_code, a.account_name, a.type

    UNION ALL

    -- LIABILITIES
    SELECT
        a.account_code,
        a.account_name,
        a.type,
        (COALESCE(SUM(jl.credit_cents), 0) - COALESCE(SUM(jl.debit_cents), 0))::BIGINT,
        'LIABILITIES'::TEXT
    FROM accounts a
    LEFT JOIN journal_lines jl ON jl.account_id = a.id
    LEFT JOIN journal_entries je ON je.id = jl.entry_id
    WHERE a.type = 'liability'
      AND (je.entry_date IS NULL OR je.entry_date <= as_of_date)
    GROUP BY a.id, a.account_code, a.account_name, a.type

    UNION ALL

    -- EQUITY
    SELECT
        a.account_code,
        a.account_name,
        a.type,
        (COALESCE(SUM(jl.credit_cents), 0) - COALESCE(SUM(jl.debit_cents), 0))::BIGINT,
        'EQUITY'::TEXT
    FROM accounts a
    LEFT JOIN journal_lines jl ON jl.account_id = a.id
    LEFT JOIN journal_entries je ON je.id = jl.entry_id
    WHERE a.type = 'equity'
      AND (je.entry_date IS NULL OR je.entry_date <= as_of_date)
    GROUP BY a.id, a.account_code, a.account_name, a.type

    ORDER BY section, account_code;
END;
$$ LANGUAGE plpgsql;

-- 8e. AP/AR Aging (應收應付帳齡)
CREATE OR REPLACE VIEW v_ar_aging AS
SELECT
    c.display_name  AS customer_name,
    COALESCE(SUM(t.amount_cents), 0) AS total_receivable_cents,
    COUNT(t.id)    AS transaction_count,
    MIN(t.created_at) AS oldest_date,
    CASE
        WHEN NOW() - MIN(t.created_at) > INTERVAL '90 days' THEN '90+ days'
        WHEN NOW() - MIN(t.created_at) > INTERVAL '60 days' THEN '61-90 days'
        WHEN NOW() - MIN(t.created_at) > INTERVAL '30 days' THEN '31-60 days'
        WHEN NOW() - MIN(t.created_at) > INTERVAL '7 days'  THEN '8-30 days'
        ELSE '0-7 days'
    END AS aging_bucket
FROM customers c
LEFT JOIN transactions t ON t.customer_id = c.id
    AND t.type IN ('payment', 'deposit', 'balance')
    AND t.status IN ('confirmed', 'pending')
LEFT JOIN refunds r ON r.customer_id = c.id
GROUP BY c.id, c.display_name
HAVING COALESCE(SUM(t.amount_cents), 0) > 0
ORDER BY SUM(t.amount_cents) DESC;


-- ============================================================
-- 9. Indexes for Accounting Layer
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_accounts_type    ON accounts(type);
CREATE INDEX IF NOT EXISTS idx_accounts_code    ON accounts(account_code);
CREATE INDEX IF NOT EXISTS idx_journal_entries_date   ON journal_entries(entry_date);
CREATE INDEX IF NOT EXISTS idx_journal_entries_source ON journal_entries(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_journal_entries_period  ON journal_entries(period_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_entry    ON journal_lines(entry_id);
CREATE INDEX IF NOT EXISTS idx_journal_lines_account   ON journal_lines(account_id);
CREATE INDEX IF NOT EXISTS idx_periods_status          ON accounting_periods(status);
CREATE INDEX IF NOT EXISTS idx_periods_dates           ON accounting_periods(start_date, end_date);


-- ============================================================
-- 10. Grant Permissions
-- ============================================================

-- Admin role (service_role key) has full access
-- Read-only roles can SELECT on views and accounts

-- Analysts / accountants: read access to reports
-- Application code: INSERT on journal_entries + journal_lines (via triggers)

COMMENT ON VIEW v_trial_balance IS
    '試算表 — 所有 account 的 debit/credit 總計。資產/支出：debit 為正；負債/權益/收入：credit 為正。';

COMMENT ON VIEW v_pnl_summary IS
    '月度損益摘要 — Revenue vs Expenses vs Net Profit，按月分組。';

COMMENT ON VIEW v_ar_aging IS
    '應收帳齡分析 — 顯示各客戶的應收帳款分布於邊個帳齡 bucket。';

COMMENT ON FUNCTION close_accounting_period IS
    '月結 procedure — 鎖定期間、產生 closing entry（Revenue → P&L）。Call: SELECT close_accounting_period(''2026-05'');';


-- ============================================================
-- ✅ Migration Complete
-- ============================================================
-- To apply:
--   npx supabase db push
--   or paste in Supabase Studio SQL Editor
--
-- Next steps after applying:
--   1. Apply audit triggers (P3): recon/supabase-audit.sql
--   2. Review COA account codes with your accountant
--   3. Test: INSERT a transaction and verify journal entry auto-creates
--   4. Run: SELECT * FROM v_trial_balance;
--      SELECT * FROM v_monthly_pnl;
-- ============================================================
