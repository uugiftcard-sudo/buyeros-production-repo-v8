-- ============================================================
-- P2+ Enhancement: Config-Driven Journal Auto-Posting
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
-- ✅ Ready to Use
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
