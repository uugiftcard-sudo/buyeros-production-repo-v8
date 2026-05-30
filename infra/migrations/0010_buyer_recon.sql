-- 0010_buyer_recon.sql
-- BuyerOS 買手對帳防偷風控系統 - Phase 1
--
-- NOTE:
-- - 金額一律用 cents (INTEGER)
-- - 大部分查詢會以 team_id + date 聚合，所以有索引
-- - 先用 TEXT 作為外部 ID（buyer_id, team_id...）方便與 Telegram / 既有系統對接

BEGIN;

-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─────────────────────────────────────────────────────────────
-- Teams / Buyers / Routes
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS recon_teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id TEXT UNIQUE NOT NULL,
    team_name TEXT NOT NULL,
    leader_telegram_id BIGINT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recon_buyers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    buyer_id TEXT UNIQUE NOT NULL,
    buyer_name TEXT NOT NULL,
    team_id TEXT REFERENCES recon_teams(team_id),
    telegram_id BIGINT UNIQUE,
    commission_rate DECIMAL(4,3) DEFAULT 0.050,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recon_routes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    route_id TEXT UNIQUE NOT NULL,
    route_name TEXT NOT NULL,
    team_id TEXT REFERENCES recon_teams(team_id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Purchase declarations (baseline)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS purchase_declarations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    declaration_id TEXT UNIQUE NOT NULL,
    buyer_id TEXT REFERENCES recon_buyers(buyer_id),
    team_id TEXT REFERENCES recon_teams(team_id),
    date DATE NOT NULL,
    source TEXT DEFAULT 'telegram',
    status TEXT DEFAULT 'pending',
    declared_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS declaration_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    declaration_id TEXT REFERENCES purchase_declarations(declaration_id),
    item_name TEXT NOT NULL,
    item_description TEXT,
    quantity INTEGER DEFAULT 1,
    unit_price_hkd INTEGER NOT NULL,
    subtotal_hkd INTEGER GENERATED ALWAYS AS (quantity * unit_price_hkd) STORED,
    is_confirmed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Receipt scans + items (AI Vision output)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS receipt_scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id TEXT UNIQUE NOT NULL,
    buyer_id TEXT REFERENCES recon_buyers(buyer_id),
    team_id TEXT REFERENCES recon_teams(team_id),
    declaration_id TEXT REFERENCES purchase_declarations(declaration_id),
    date DATE NOT NULL,
    image_url TEXT NOT NULL,
    original_image_url TEXT,
    watermark_applied BOOLEAN DEFAULT FALSE,
    image_hash TEXT,
    raw_text TEXT,
    total_amount_hkd INTEGER,
    currency TEXT DEFAULT 'HKD',
    scan_status TEXT DEFAULT 'pending',
    scan_error TEXT,
    ai_provider TEXT,
    ai_confidence DECIMAL(3,2),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS receipt_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id TEXT REFERENCES receipt_scans(scan_id),
    item_name TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit_price_hkd INTEGER,
    subtotal_hkd INTEGER,
    ai_confidence DECIMAL(3,2),
    is_matched BOOLEAN,
    matched_declaration_item_id UUID REFERENCES declaration_items(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Item comparison (risk engine output)
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS item_comparisons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    comparison_id TEXT UNIQUE NOT NULL,
    declaration_id TEXT REFERENCES purchase_declarations(declaration_id),
    scan_id TEXT REFERENCES receipt_scans(scan_id),
    buyer_id TEXT REFERENCES recon_buyers(buyer_id),
    team_id TEXT REFERENCES recon_teams(team_id),
    date DATE NOT NULL,

    has_missing_items BOOLEAN DEFAULT FALSE,
    has_undeclared_items BOOLEAN DEFAULT FALSE,
    has_extra_items BOOLEAN DEFAULT FALSE,
    has_price_mismatch BOOLEAN DEFAULT FALSE,
    has_quantity_mismatch BOOLEAN DEFAULT FALSE,
    has_unmatched_declared BOOLEAN DEFAULT FALSE,
    all_matched BOOLEAN DEFAULT FALSE,

    declared_total_hkd INTEGER DEFAULT 0,
    scanned_total_hkd INTEGER DEFAULT 0,
    price_difference_hkd INTEGER DEFAULT 0,

    missing_items JSONB DEFAULT '[]',
    undeclared_items JSONB DEFAULT '[]',
    mismatched_items JSONB DEFAULT '[]',

    risk_level TEXT DEFAULT 'low',
    risk_flags JSONB DEFAULT '[]',

    status TEXT DEFAULT 'pending',
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    resolution_notes TEXT,

    escalated BOOLEAN DEFAULT FALSE,
    escalated_at TIMESTAMPTZ,
    escalation_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Returns
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS returns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    return_id TEXT UNIQUE NOT NULL,
    buyer_id TEXT REFERENCES recon_buyers(buyer_id),
    team_id TEXT REFERENCES recon_teams(team_id),
    declaration_id TEXT REFERENCES purchase_declarations(declaration_id),
    date DATE NOT NULL,
    image_url TEXT NOT NULL,
    raw_text TEXT,
    returned_item_name TEXT,
    returned_item_description TEXT,
    quantity INTEGER DEFAULT 1,
    refund_amount_hkd INTEGER,
    ai_confidence DECIMAL(3,2),
    ai_provider TEXT,
    scan_status TEXT DEFAULT 'pending',
    status TEXT DEFAULT 'pending',
    confirmed_by TEXT,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Daily / Weekly reconciliation + commissions
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS recon_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recon_id TEXT UNIQUE NOT NULL,
    team_id TEXT REFERENCES recon_teams(team_id),
    date DATE NOT NULL,
    period_type TEXT DEFAULT 'daily',

    total_declared_hkd INTEGER DEFAULT 0,
    total_scanned_hkd INTEGER DEFAULT 0,
    total_income_diff_hkd INTEGER DEFAULT 0,

    total_returns_hkd INTEGER DEFAULT 0,
    return_count INTEGER DEFAULT 0,

    total_expenses_hkd INTEGER DEFAULT 0,
    expense_count INTEGER DEFAULT 0,

    total_missing_items INTEGER DEFAULT 0,
    total_price_mismatches INTEGER DEFAULT 0,
    total_risk_alerts INTEGER DEFAULT 0,
    critical_alerts INTEGER DEFAULT 0,

    net_sales_hkd INTEGER GENERATED ALWAYS AS (
        total_scanned_hkd - total_returns_hkd - total_expenses_hkd
    ) STORED,
    total_commission_hkd INTEGER DEFAULT 0,
    net_profit_hkd INTEGER GENERATED ALWAYS AS (
        (total_scanned_hkd - total_returns_hkd - total_expenses_hkd) - total_commission_hkd
    ) STORED,

    status TEXT DEFAULT 'draft',
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recon_weekly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recon_id TEXT UNIQUE NOT NULL,
    team_id TEXT REFERENCES recon_teams(team_id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    total_declared_hkd INTEGER DEFAULT 0,
    total_scanned_hkd INTEGER DEFAULT 0,
    total_income_diff_hkd INTEGER DEFAULT 0,
    total_returns_hkd INTEGER DEFAULT 0,
    total_expenses_hkd INTEGER DEFAULT 0,
    total_commission_hkd INTEGER DEFAULT 0,
    net_profit_hkd INTEGER DEFAULT 0,

    total_missing_items INTEGER DEFAULT 0,
    total_price_mismatches INTEGER DEFAULT 0,
    total_risk_alerts INTEGER DEFAULT 0,
    critical_alerts INTEGER DEFAULT 0,

    daily_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'draft',
    approved_by TEXT,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS recon_buyer_commission (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commission_id TEXT UNIQUE NOT NULL,
    buyer_id TEXT REFERENCES recon_buyers(buyer_id),
    team_id TEXT REFERENCES recon_teams(team_id),
    recon_id TEXT REFERENCES recon_daily(recon_id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    period_type TEXT NOT NULL,

    gross_sales_hkd INTEGER DEFAULT 0,
    returns_hkd INTEGER DEFAULT 0,
    expenses_hkd INTEGER DEFAULT 0,
    net_sales_hkd INTEGER DEFAULT 0,
    commission_rate DECIMAL(4,3),
    commission_hkd INTEGER DEFAULT 0,

    status TEXT DEFAULT 'pending',
    paid_at TIMESTAMPTZ,
    paid_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Bank statements / transactions / reconciliations
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS bank_statements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    statement_id TEXT UNIQUE NOT NULL,
    team_id TEXT REFERENCES recon_teams(team_id),
    date DATE NOT NULL,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,

    total_deposits_hkd INTEGER DEFAULT 0,
    deposit_count INTEGER DEFAULT 0,
    total_withdrawals_hkd INTEGER DEFAULT 0,
    withdrawal_count INTEGER DEFAULT 0,

    opening_balance_hkd INTEGER DEFAULT 0,
    closing_balance_hkd INTEGER DEFAULT 0,

    raw_csv_url TEXT,
    raw_entry_count INTEGER,
    currency TEXT DEFAULT 'HKD',

    source TEXT DEFAULT 'upload',
    uploaded_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(team_id, period_start, period_end)
);

CREATE TABLE IF NOT EXISTS bank_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    statement_id TEXT REFERENCES bank_statements(statement_id),
    team_id TEXT REFERENCES recon_teams(team_id),
    date DATE NOT NULL,

    transaction_ref TEXT,
    description TEXT,
    transaction_type TEXT,
    amount_hkd INTEGER NOT NULL,
    balance_after_hkd INTEGER,
    category TEXT,

    is_reconciled BOOLEAN DEFAULT FALSE,
    reconciled_with TEXT,
    reconciled_at TIMESTAMPTZ,
    reconciled_by TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bank_reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recon_id TEXT UNIQUE NOT NULL,
    team_id TEXT REFERENCES recon_teams(team_id),
    date DATE NOT NULL,

    bank_deposits_hkd INTEGER DEFAULT 0,
    bank_withdrawals_hkd INTEGER DEFAULT 0,
    bank_closing_balance_hkd INTEGER DEFAULT 0,

    system_sales_hkd INTEGER DEFAULT 0,
    system_refunds_hkd INTEGER DEFAULT 0,
    system_payouts_hkd INTEGER DEFAULT 0,
    system_expenses_hkd INTEGER DEFAULT 0,
    system_closing_balance_hkd INTEGER DEFAULT 0,

    has_missing_deposits BOOLEAN DEFAULT FALSE,
    has_extra_deposits BOOLEAN DEFAULT FALSE,
    has_missing_refunds BOOLEAN DEFAULT FALSE,
    has_suspicious_pattern BOOLEAN DEFAULT FALSE,

    risk_level TEXT DEFAULT 'low',
    risk_flags JSONB DEFAULT '[]',

    status TEXT DEFAULT 'pending',
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    resolution_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Payment cards + refund card verifications
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS payment_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    card_id TEXT UNIQUE NOT NULL,
    buyer_id TEXT REFERENCES recon_buyers(buyer_id),
    team_id TEXT REFERENCES recon_teams(team_id),

    card_last4 TEXT NOT NULL,
    card_type TEXT,
    card_holder_name TEXT,
    is_verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    verified_by TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS refund_card_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    verification_id TEXT UNIQUE NOT NULL,
    buyer_id TEXT REFERENCES recon_buyers(buyer_id),
    team_id TEXT REFERENCES recon_teams(team_id),
    return_id TEXT REFERENCES returns(return_id),

    original_transaction_id TEXT,
    original_card_last4 TEXT,

    refund_card_last4 TEXT,
    refund_amount_hkd INTEGER,

    card_match BOOLEAN,
    card_verified BOOLEAN,
    verification_status TEXT DEFAULT 'pending',

    risk_level TEXT DEFAULT 'low',
    risk_flags JSONB DEFAULT '[]',

    verified_by TEXT,
    verified_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─────────────────────────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_purchase_declarations_date ON purchase_declarations(date);
CREATE INDEX IF NOT EXISTS idx_purchase_declarations_buyer ON purchase_declarations(buyer_id);
CREATE INDEX IF NOT EXISTS idx_purchase_declarations_status ON purchase_declarations(status);

CREATE INDEX IF NOT EXISTS idx_receipt_scans_date ON receipt_scans(date);
CREATE INDEX IF NOT EXISTS idx_receipt_scans_buyer ON receipt_scans(buyer_id);
CREATE INDEX IF NOT EXISTS idx_receipt_scans_status ON receipt_scans(scan_status);
CREATE INDEX IF NOT EXISTS idx_receipt_scans_decl ON receipt_scans(declaration_id);
CREATE INDEX IF NOT EXISTS idx_receipt_scans_image_hash ON receipt_scans(image_hash);

CREATE INDEX IF NOT EXISTS idx_item_comparisons_date ON item_comparisons(date);
CREATE INDEX IF NOT EXISTS idx_item_comparisons_buyer ON item_comparisons(buyer_id);
CREATE INDEX IF NOT EXISTS idx_item_comparisons_team ON item_comparisons(team_id);
CREATE INDEX IF NOT EXISTS idx_item_comparisons_risk ON item_comparisons(risk_level);
CREATE INDEX IF NOT EXISTS idx_item_comparisons_decl ON item_comparisons(declaration_id);
CREATE INDEX IF NOT EXISTS idx_item_comparisons_scan ON item_comparisons(scan_id);
CREATE INDEX IF NOT EXISTS idx_item_comparisons_status ON item_comparisons(status);

CREATE INDEX IF NOT EXISTS idx_returns_date ON returns(date);
CREATE INDEX IF NOT EXISTS idx_returns_buyer ON returns(buyer_id);
CREATE INDEX IF NOT EXISTS idx_returns_team ON returns(team_id);

CREATE INDEX IF NOT EXISTS idx_recon_daily_date ON recon_daily(date);
CREATE INDEX IF NOT EXISTS idx_recon_daily_team ON recon_daily(team_id);

CREATE INDEX IF NOT EXISTS idx_recon_weekly_team ON recon_weekly(team_id);
CREATE INDEX IF NOT EXISTS idx_recon_weekly_period ON recon_weekly(period_start, period_end);

CREATE INDEX IF NOT EXISTS idx_recon_buyer_commission_buyer ON recon_buyer_commission(buyer_id);
CREATE INDEX IF NOT EXISTS idx_recon_buyer_commission_team ON recon_buyer_commission(team_id);

CREATE INDEX IF NOT EXISTS idx_bank_statements_date ON bank_statements(date);
CREATE INDEX IF NOT EXISTS idx_bank_statements_team ON bank_statements(team_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_date ON bank_transactions(date);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_team ON bank_transactions(team_id);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_reconciled ON bank_transactions(is_reconciled);
CREATE INDEX IF NOT EXISTS idx_bank_reconciliations_date ON bank_reconciliations(date);
CREATE INDEX IF NOT EXISTS idx_bank_reconciliations_team ON bank_reconciliations(team_id);
CREATE INDEX IF NOT EXISTS idx_bank_reconciliations_risk ON bank_reconciliations(risk_level);

CREATE INDEX IF NOT EXISTS idx_payment_cards_buyer ON payment_cards(buyer_id);
CREATE INDEX IF NOT EXISTS idx_payment_cards_last4 ON payment_cards(card_last4);
CREATE INDEX IF NOT EXISTS idx_refund_card_verif_return ON refund_card_verifications(return_id);
CREATE INDEX IF NOT EXISTS idx_refund_card_verif_buyer ON refund_card_verifications(buyer_id);

COMMIT;
