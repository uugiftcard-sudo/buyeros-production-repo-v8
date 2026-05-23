-- ============================================================
-- BuyerOS — 企業級功能遷移
-- Version: 0004_enterprise.sql
-- ============================================================
-- 新增：
--   - admin_users (管理員/買手角色表)
--   - buyer_teams (買手團隊)
--   - buyer_team_members (團隊成員)
--   - audit_log (已有，用於確保存在)
--   - 增強 orders 表（priority, source_channel, etc.）
--   - 增強 buyers 表（team_id, admin_notes）
--   - View: v_orders_analytics (訂單分析)
--   - View: v_team_performance (團隊表現)
--   - Trigger: 更新 updated_at (補足)
-- ============================================================

-- ─── admin_users ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS admin_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- identity
    telegram_user_id BIGINT UNIQUE,
    email TEXT UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'staff' CHECK (role IN (
        'owner',      -- 創辦人，擁有所有權限
        'admin',      -- 全域管理員
        'manager',    -- 部門經理，可管理特定團隊
        'supervisor', -- 主管，可審批/查看
        'staff'       -- 普通員工，只可操作自己負責的範圍
    )),
    team_id UUID, -- 主管/員工所屬團隊
    -- access control
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    -- permissions (JSONB for fine-grained control)
    permissions JSONB DEFAULT '[]',
    -- profile
    phone TEXT,
    avatar_url TEXT,
    notes TEXT
);

ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;

-- Admin can do everything
CREATE POLICY "admin_users_all" ON admin_users FOR ALL
    USING (TRUE);

-- ─── buyer_teams ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS buyer_teams (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    team_name TEXT NOT NULL,
    team_code TEXT UNIQUE NOT NULL, -- e.g. "TEAM-A", "TEAM-B"
    description TEXT,
    manager_id UUID REFERENCES admin_users(id),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    color TEXT DEFAULT '#4f46e5', -- for UI badges
    target_orders_monthly INT DEFAULT 50, -- 月目標訂單數
    target_revenue_monthly_cents INT DEFAULT 5000000, -- 月目標收入 HK$50,000
    notes TEXT
);

ALTER TABLE buyer_teams ENABLE ROW LEVEL SECURITY;
CREATE POLICY "buyer_teams_all" ON buyer_teams FOR ALL USING (TRUE);

-- ─── buyer_team_members ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS buyer_team_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    team_id UUID NOT NULL REFERENCES buyer_teams(id) ON DELETE CASCADE,
    buyer_id UUID NOT NULL REFERENCES buyers(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('leader', 'member', 'trainee')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(team_id, buyer_id)
);

ALTER TABLE buyer_team_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY "buyer_team_members_all" ON buyer_team_members FOR ALL USING (TRUE);

-- ─── Add columns to existing tables ────────────────────────────

-- orders: add priority + tags + source_channel
ALTER TABLE orders ADD COLUMN IF NOT EXISTS priority TEXT DEFAULT 'normal'
    CHECK (priority IN ('low', 'normal', 'high', 'urgent'));
ALTER TABLE orders ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';
ALTER TABLE orders ADD COLUMN IF NOT EXISTS source_channel TEXT DEFAULT 'telegram'
    CHECK (source_channel IN ('telegram', 'web', 'admin', 'api', 'referral'));

-- buyers: add team membership
ALTER TABLE buyers ADD COLUMN IF NOT EXISTS team_id UUID REFERENCES buyer_teams(id);
ALTER TABLE buyers ADD COLUMN IF NOT EXISTS admin_notes TEXT;

-- audit_log: ensure exists with full schema
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    table_name TEXT NOT NULL,
    row_id UUID NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('INSERT', 'UPDATE', 'DELETE')),
    old_data JSONB,
    new_data JSONB,
    changed_by UUID,
    changed_by_role TEXT, -- 'owner', 'admin', 'manager', 'supervisor', 'staff', 'buyer', 'customer', 'system'
    changed_by_name TEXT, -- human-readable name for audit trail
    ip_address INET,
    tg_message_id BIGINT,
    reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_audit_log_created ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_table_row ON audit_log(table_name, row_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_changed_by ON audit_log(changed_by);

ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "audit_log_admin_read" ON audit_log FOR SELECT USING (TRUE);
CREATE POLICY "audit_log_admin_write" ON audit_log FOR INSERT WITH CHECK (TRUE);

-- ─── VIEWS ─────────────────────────────────────────────────────

-- v_orders_analytics: 訂單分析視圖
CREATE OR REPLACE VIEW v_orders_analytics AS
SELECT
    DATE_TRUNC('day', o.created_at)::DATE AS order_date,
    COUNT(*) AS total_orders,
    COUNT(*) FILTER (WHERE o.status = 'pending') AS pending_orders,
    COUNT(*) FILTER (WHERE o.status = 'completed') AS completed_orders,
    COUNT(*) FILTER (WHERE o.status = 'cancelled') AS cancelled_orders,
    SUM(o.total_amount_cents) AS total_revenue_cents,
    SUM(o.deposit_paid_cents) AS total_deposit_cents,
    AVG(o.total_amount_cents)::INT AS avg_order_value_cents,
    COUNT(DISTINCT o.customer_id) AS unique_customers,
    COUNT(DISTINCT o.assigned_buyer_id) AS active_buyers
FROM orders o
WHERE o.created_at >= NOW() - INTERVAL '365 days'
GROUP BY DATE_TRUNC('day', o.created_at)
ORDER BY order_date DESC;

-- v_team_performance: 團隊表現視圖
CREATE OR REPLACE VIEW v_team_performance AS
SELECT
    bt.id AS team_id,
    bt.team_name,
    bt.team_code,
    COUNT(DISTINCT btm.buyer_id) AS member_count,
    COUNT(DISTINCT o.id) AS total_orders,
    COUNT(DISTINCT o.id) FILTER (WHERE o.status = 'completed') AS completed_orders,
    COALESCE(SUM(o.total_amount_cents) FILTER (WHERE o.status = 'completed'), 0) AS total_revenue_cents,
    COALESCE(AVG(o.total_amount_cents) FILTER (WHERE o.status = 'completed'), 0)::INT AS avg_order_value_cents,
    COUNT(DISTINCT o.id) FILTER (
        WHERE o.created_at >= DATE_TRUNC('month', NOW())
    ) AS monthly_orders,
    COALESCE(SUM(o.total_amount_cents) FILTER (
        WHERE o.status = 'completed' AND o.created_at >= DATE_TRUNC('month', NOW())
    ), 0) AS monthly_revenue_cents,
    bt.target_orders_monthly,
    bt.target_revenue_monthly_cents,
    ROUND(
        COUNT(DISTINCT o.id) FILTER (WHERE o.created_at >= DATE_TRUNC('month', NOW()))::NUMERIC
        / NULLIF(bt.target_orders_monthly, 0) * 100
    ) AS monthly_orders_pct,
    ROUND(
        COALESCE(SUM(o.total_amount_cents) FILTER (
            WHERE o.status = 'completed' AND o.created_at >= DATE_TRUNC('month', NOW())
        ), 0)::NUMERIC
        / NULLIF(bt.target_revenue_monthly_cents, 0) * 100
    ) AS monthly_revenue_pct
FROM buyer_teams bt
LEFT JOIN buyer_team_members btm ON btm.team_id = bt.id AND btm.is_active = TRUE
LEFT JOIN buyers b ON b.id = btm.buyer_id AND b.is_active = TRUE
LEFT JOIN orders o ON o.assigned_buyer_id = b.id
WHERE bt.is_active = TRUE
GROUP BY bt.id, bt.team_name, bt.team_code, bt.target_orders_monthly, bt.target_revenue_monthly_cents;

-- v_audit_log_summary: 審計日誌摘要
CREATE OR REPLACE VIEW v_audit_log_summary AS
SELECT
    created_at::DATE AS log_date,
    table_name,
    action,
    changed_by_role,
    COUNT(*) AS event_count,
    COUNT(DISTINCT changed_by) AS unique_users
FROM audit_log
WHERE created_at >= NOW() - INTERVAL '90 days'
GROUP BY created_at::DATE, table_name, action, changed_by_role
ORDER BY log_date DESC, event_count DESC;

-- ─── Seed: Default admin user ───────────────────────────────────
-- NOTE: Replace with your Telegram ID and run once
-- INSERT INTO admin_users (display_name, role, telegram_user_id, permissions)
-- VALUES ('Admin', 'owner', YOUR_TELEGRAM_USER_ID, '["*"]')
-- ON CONFLICT (telegram_user_id) DO NOTHING;
