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


-- ============================================================
-- P2+ Enhancement: Config-Driven Journal Auto-Posting
-- (merged from 0002b_config_driven_posting.sql)
-- ============================================================
-- Problem: P2's post_transaction_journal() hardcodes enum values.
-- Solution: A journal_posting_rules table that maps business events
--           to accounting entries WITHOUT modifying trigger SQL.
--
-- Benefits:
--   - No hardcoded enum values
--   - Add new transaction types without code change
--   - Business user (admin) can update rules without developer
--   - Self-documenting: rules are readable in the table
--
-- How it works:
--   1. Define rules in journal_posting_rules (seeded below)
--   2. post_transaction_journal_from_rules() reads rules and posts
--   3. Apply rules via a stored procedure, not raw trigger SQL
--
-- Usage (after migration applies):
--   SELECT apply_journal_rule('transaction', '<transaction-uuid>');
-- ============================================================


-- ============================================================
-- A. Journal Posting Rules Config Table
-- ============================================================

CREATE TABLE IF NOT EXISTS journal_posting_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type     TEXT NOT NULL,      -- 'transaction' | 'refund' | 'settlement'
    event_value     TEXT NOT NULL,      -- e.g. 'payment', 'deposit', 'commission'
    status_filter   TEXT,               -- NULL = any status; or e.g. 'completed'
    debit_account   TEXT NOT NULL,      -- account_code to DEBIT
    credit_account  TEXT NOT NULL,      -- account_code to CREDIT
    memo_template   TEXT NOT NULL,      -- PG template string: e.g. 'Payment: {{source_ref}}'
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    priority        INT NOT NULL DEFAULT 0,  -- higher = applied first
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- One rule per source_type + event_value combination
    CONSTRAINT unique_rule UNIQUE (source_type, event_value, status_filter)
);

-- Seed rules for BUYEROS 代購平台
-- Adjust debit/credit account codes based on your verified COA
INSERT INTO journal_posting_rules
    (source_type, event_value, status_filter, debit_account, credit_account, memo_template, priority)
VALUES
    -- =============================================
    -- TRANSACTIONS
    -- =============================================
    -- Customer pays deposit
    ('transaction', 'deposit',  NULL,
     '1101',   -- Debit: Bank (cash in)
     '4101',   -- Credit: Procurement Revenue
     'Deposit received: {{source_ref}}',
     10),

    -- Customer pays full / balance
    ('transaction', 'payment', NULL,
     '1101',   -- Debit: Bank
     '4101',   -- Credit: Revenue
     'Payment received: {{source_ref}}',
     10),

    -- Balance payment
    ('transaction', 'balance', NULL,
     '1101',   -- Debit: Bank
     '4101',   -- Credit: Revenue
     'Balance payment: {{source_ref}}',
     10),

    -- Commission from buyer
    ('transaction', 'commission', NULL,
     '1101',   -- Debit: Bank
     '4102',   -- Credit: Handling Fee Revenue
     'Commission received: {{source_ref}}',
     10),

    -- Payment reversal / failed
    ('transaction', 'failed', NULL,
     '1101',   -- Debit: Bank (reversing)
     '1101',   -- Credit: Bank (just for balance — real reversal needs adjustment)
     'Payment failed/reversed: {{source_ref}}',
     5),

    -- =============================================
    -- REFUNDS
    -- =============================================
    -- Refund processed → Debit expense, Credit cash
    ('refund', 'approved',  NULL,
     '5201',   -- Debit: Refund Expense
     '1101',   -- Credit: Bank
     'Refund issued: {{source_ref}} — {{reason}}',
     10),

    ('refund', 'processing', NULL,
     '5201',
     '1101',
     'Refund processing: {{source_ref}}',
     8),

    ('refund', 'completed', NULL,
     '5201',
     '1101',
     'Refund completed: {{source_ref}}',
     10),

    -- =============================================
    -- SETTLEMENTS
    -- =============================================
    -- Buyer settlement paid → Debit AP Buyer, Credit Bank
    ('settlement', 'paid', NULL,
     '2102',   -- Debit: AP Buyer Settlement (liability reduced)
     '1101',   -- Credit: Bank
     'Settlement paid to buyer: {{source_ref}}',
     10)
ON CONFLICT (source_type, event_value, status_filter) DO NOTHING;

-- ⚠️ IF YOUR ACTUAL ENUM VALUES DIFFER FROM ABOVE,
-- update the `event_value` column to match your real data.
-- Run: SELECT DISTINCT type FROM transactions;
--      SELECT DISTINCT status FROM refunds;


-- ============================================================
-- B. Helper: Get account ID from account code
-- ============================================================

CREATE OR REPLACE FUNCTION get_account_id(p_account_code TEXT)
RETURNS UUID AS $$
DECLARE
    result UUID;
BEGIN
    SELECT id INTO result FROM accounts WHERE account_code = p_account_code;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Account code "%" not found in accounts table', p_account_code;
    END IF;
    RETURN result;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- C. Config-Driven Journal Posting Function
-- ============================================================

CREATE OR REPLACE FUNCTION apply_journal_rule(
    p_source_type  TEXT,
    p_source_id   UUID
)
RETURNS UUID AS $$
DECLARE
    rule           RECORD;
    entry_id       UUID;
    memo_text      TEXT;
    source_ref     TEXT;
    source_date    DATE;
    source_amount  INT;
    source_reason  TEXT;
BEGIN
    -- Fetch source record based on type
    IF p_source_type = 'transaction' THEN
        SELECT t.transaction_number, t.amount_cents,
               COALESCE(t.paid_at::DATE, t.created_at::DATE), t.memo
        INTO source_ref, source_amount, source_date, memo_text
        FROM transactions t WHERE t.id = p_source_id;

        -- Find matching rule (by type from source record)
        SELECT r.* INTO rule
        FROM journal_posting_rules r
        WHERE r.source_type = 'transaction'
          AND r.event_value = (SELECT type FROM transactions WHERE id = p_source_id)
          AND r.is_active = TRUE
        ORDER BY r.priority DESC
        LIMIT 1;

    ELSIF p_source_type = 'refund' THEN
        SELECT r.refund_number, r.amount_cents,
               COALESCE(r.processed_at::DATE, r.updated_at::DATE),
               COALESCE(r.reason, '')
        INTO source_ref, source_amount, source_date, source_reason
        FROM refunds r WHERE r.id = p_source_id;

        SELECT r.* INTO rule
        FROM journal_posting_rules r
        WHERE r.source_type = 'refund'
          AND r.event_value = (SELECT status FROM refunds WHERE id = p_source_id)
          AND r.is_active = TRUE
        ORDER BY r.priority DESC
        LIMIT 1;

        -- Build memo from template
        memo_text := REPLACE(rule.memo_template, '{{source_ref}}', source_ref);
        memo_text := REPLACE(memo_text, '{{reason}}', COALESCE(source_reason, ''));

    ELSIF p_source_type = 'settlement' THEN
        SELECT s.settlement_number, s.commission_amount_cents,
               COALESCE(s.paid_at::DATE, s.updated_at::DATE)
        INTO source_ref, source_amount, source_date
        FROM settlements s WHERE s.id = p_source_id;

        SELECT r.* INTO rule
        FROM journal_posting_rules r
        WHERE r.source_type = 'settlement'
          AND r.event_value = (SELECT status FROM settlements WHERE id = p_source_id)
          AND r.is_active = TRUE
        ORDER BY r.priority DESC
        LIMIT 1;

    END IF;

    -- No matching rule found
    IF rule IS NULL THEN
        RAISE NOTICE 'No active rule found for source_type=%, source_id=%',
            p_source_type, p_source_id;
        RETURN NULL;
    END IF;

    -- Generate memo if not already set
    IF memo_text IS NULL THEN
        memo_text := REPLACE(rule.memo_template, '{{source_ref}}', COALESCE(source_ref, p_source_id::TEXT));
    END IF;

    -- Create journal entry
    INSERT INTO journal_entries (
        entry_number, entry_date, source_type, source_id, source_ref,
        memo, posted_by, posted_by_role
    ) VALUES (
        next_entry_number(source_date),
        source_date,
        p_source_type,
        p_source_id,
        source_ref,
        memo_text,
        'system', 'system'
    ) RETURNING id INTO entry_id;

    -- Debit line
    INSERT INTO journal_lines (entry_id, account_id, debit_cents, memo)
    VALUES (
        entry_id,
        get_account_id(rule.debit_account),
        source_amount,
        'DR: ' || memo_text
    );

    -- Credit line
    INSERT INTO journal_lines (entry_id, account_id, credit_cents, memo)
    VALUES (
        entry_id,
        get_account_id(rule.credit_account),
        source_amount,
        'CR: ' || memo_text
    );

    -- Update source record with journal entry link
    IF p_source_type = 'transaction' THEN
        UPDATE transactions SET id = id WHERE id = p_source_id;
        -- TODO: add journal_entry_id column to transactions, then:
        -- UPDATE transactions SET journal_entry_id = entry_id WHERE id = p_source_id;
    ELSIF p_source_type = 'refund' THEN
        UPDATE refunds SET id = id WHERE id = p_source_id;
        -- TODO: add journal_entry_id column to refunds, then:
        -- UPDATE refunds SET journal_entry_id = entry_id WHERE id = p_source_id;
    END IF;

    RETURN entry_id;

EXCEPTION WHEN OTHERS THEN
    RAISE WARNING 'apply_journal_rule failed for %/%: %',
        p_source_type, p_source_id, SQLERRM;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- D. One-Time Backfill: Apply rules to existing records
-- ============================================================

-- Run this AFTER migration applies, to create journal entries for
-- all existing transactions and refunds that don't have one.

CREATE OR REPLACE FUNCTION backfill_journal_entries(
    p_source_type TEXT DEFAULT NULL  -- NULL = all types
)
RETURNS TABLE (source_type TEXT, posted_count BIGINT, skipped_count BIGINT) AS $$
DECLARE
    rec RECORD;
BEGIN
    -- Backfill transactions
    IF p_source_type IS NULL OR p_source_type = 'transaction' THEN
        FOR rec IN
            SELECT apply_journal_rule('transaction', id) AS entry_id
            FROM transactions
            WHERE created_at > '2024-01-01'
            ORDER BY created_at
            LIMIT 10000  -- safety: process in batches if large table
        LOOP
            IF rec.entry_id IS NOT NULL THEN
                posted := posted + 1;
            ELSE
                skipped := skipped + 1;
            END IF;
        END LOOP;

        RETURN QUERY SELECT 'transaction'::TEXT, posted::BIGINT, skipped::BIGINT;
        posted := 0;
        skipped := 0;
    END IF;

    -- Backfill refunds
    IF p_source_type IS NULL OR p_source_type = 'refund' THEN
        FOR rec IN
            SELECT apply_journal_rule('refund', id) AS entry_id
            FROM refunds
            WHERE created_at > '2024-01-01'
            ORDER BY created_at
            LIMIT 10000
        LOOP
            IF rec.entry_id IS NOT NULL THEN
                posted := posted + 1;
            ELSE
                skipped := skipped + 1;
            END IF;
        END LOOP;

        RETURN QUERY SELECT 'refund'::TEXT, posted::BIGINT, skipped::BIGINT;
    END IF;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- E. Convenience: Post for ALL pending transactions
-- ============================================================

-- Usage: SELECT * FROM post_all_pending_journal_entries();
CREATE OR REPLACE FUNCTION post_all_pending_journal_entries()
RETURNS TABLE (source_type TEXT, source_id UUID, entry_id UUID, status TEXT) AS $$
DECLARE
    rec RECORD;
BEGIN
    FOR rec IN
        SELECT 'transaction' AS st, id FROM transactions
        UNION ALL
        SELECT 'refund', id FROM refunds
    LOOP
        BEGIN
            SELECT apply_journal_rule(rec.st, rec.id) INTO entry_id;
            status := CASE WHEN entry_id IS NOT NULL THEN 'posted' ELSE 'skipped' END;
            source_id := rec.id;
            source_type := rec.st;
            RETURN NEXT;
        EXCEPTION WHEN OTHERS THEN
            status := 'error: ' || SQLERRM;
            source_id := rec.id;
            source_type := rec.st;
            entry_id := NULL;
            RETURN NEXT;
        END;
    END LOOP;
END;
$$ LANGUAGE plpgsql;


-- ============================================================
-- ✅ Config-Driven Posting Merged
-- ============================================================
-- After applying this migration:
--
-- 1. Verify rules match your actual enum values:
--    SELECT * FROM journal_posting_rules;
--    -- Compare with: SELECT DISTINCT type FROM transactions;
--    --               SELECT DISTINCT status FROM refunds;
--
-- 2. Update event_value in journal_posting_rules if different
--
-- 3. Post journal entries for existing data:
--    SELECT * FROM backfill_journal_entries();
--
-- 4. Or post one by one:
--    SELECT apply_journal_rule('transaction', '<uuid>');
--
-- 5. Verify results:
--    SELECT * FROM v_trial_balance;
-- ============================================================
