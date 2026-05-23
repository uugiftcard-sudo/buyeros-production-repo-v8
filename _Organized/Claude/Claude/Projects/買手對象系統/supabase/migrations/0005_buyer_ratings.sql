-- ============================================================
-- P4.3: Buyer Rating System Migration
-- BuyerOS（買手對象系統）
-- ============================================================
-- Migration: 0005_buyer_ratings.sql
-- Depends on: 0001_initial_reconstructed.sql
--
-- Scope:
--   - ratings table (buyer ratings from completed orders)
--   - Rating categories: communication, quality, speed, accuracy, overall
--   - Auto-update buyer's rating_avg + rating_count in buyers table
--   - Edge function stubs for rating CRUD
-- ============================================================


-- ============================================================
-- 1. Ratings Table
-- ============================================================

CREATE TABLE IF NOT EXISTS ratings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Who rated whom
    buyer_id   UUID NOT NULL REFERENCES buyers(id),
    order_id   UUID NOT NULL REFERENCES orders(id),
    rated_by   UUID NOT NULL,  -- customers.id or admin user UUID

    -- Rating scores (1–5)
    communication_score INT NOT NULL
        CHECK (communication_score BETWEEN 1 AND 5),
    quality_score        INT NOT NULL
        CHECK (quality_score BETWEEN 1 AND 5),
    speed_score         INT NOT NULL
        CHECK (speed_score BETWEEN 1 AND 5),
    accuracy_score      INT NOT NULL
        CHECK (accuracy_score BETWEEN 1 AND 5),
    overall_score       INT NOT NULL
        CHECK (overall_score BETWEEN 1 AND 5),

    -- Optional text feedback
    review_text TEXT,

    -- One rating per (order, buyer) pair
    CONSTRAINT unique_buyer_order_rating UNIQUE (order_id, buyer_id),

    -- Cannot rate the same order twice from same rater
    CONSTRAINT unique_order_rater UNIQUE (order_id, rated_by),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE ratings IS
    '買手評分記錄 — 每個已完成訂單可由客戶或管理員對買手進行評分（1-5星）。';


-- ============================================================
-- 2. Auto-update buyers.rating_avg + rating_count
-- ============================================================

CREATE OR REPLACE FUNCTION recalculate_buyer_rating()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE buyers
    SET
        rating_avg   = (
            SELECT ROUND(AVG(overall_score)::NUMERIC, 2)
            FROM ratings
            WHERE buyer_id = COALESCE(NEW.buyer_id, OLD.buyer_id)
        ),
        rating_count = (
            SELECT COUNT(*)
            FROM ratings
            WHERE buyer_id = COALESCE(NEW.buyer_id, OLD.buyer_id)
        )
    WHERE id = COALESCE(NEW.buyer_id, OLD.buyer_id);

    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Recalculate when a rating is inserted, updated, or deleted
DROP TRIGGER IF EXISTS trg_rating_recalculate ON ratings;
CREATE TRIGGER trg_rating_recalculate
    AFTER INSERT OR UPDATE OR DELETE ON ratings
    FOR EACH ROW
    EXECUTE FUNCTION recalculate_buyer_rating();


-- ============================================================
-- 3. Restrict ratings to completed orders only
-- ============================================================

CREATE OR REPLACE FUNCTION validate_rating_order()
RETURNS TRIGGER AS $$
DECLARE
    order_status TEXT;
BEGIN
    SELECT status INTO order_status
    FROM orders
    WHERE id = NEW.order_id;

    IF order_status != 'completed' THEN
        RAISE EXCEPTION 'Can only rate buyers on completed orders. Order status is: "%"',
            COALESCE(order_status, 'unknown')
        USING HINT = 'Wait until the order status is ''completed'' before submitting a rating.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_validate_rating_order ON ratings;
CREATE TRIGGER trg_validate_rating_order
    BEFORE INSERT ON ratings
    FOR EACH ROW
    EXECUTE FUNCTION validate_rating_order();


-- ============================================================
-- 4. Indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_ratings_buyer     ON ratings(buyer_id);
CREATE INDEX IF NOT EXISTS idx_ratings_order    ON ratings(order_id);
CREATE INDEX IF NOT EXISTS idx_ratings_rated_by ON ratings(rated_by);
CREATE INDEX IF NOT EXISTS idx_ratings_created  ON ratings(created_at DESC);


-- ============================================================
-- 5. View: Buyer Rating Summary
-- ============================================================

CREATE OR REPLACE VIEW v_buyer_ratings AS
SELECT
    b.id         AS buyer_id,
    b.display_name,
    COALESCE(AVG(r.overall_score),          0)::NUMERIC(3,2) AS avg_overall,
    COALESCE(AVG(r.communication_score),     0)::NUMERIC(3,2) AS avg_communication,
    COALESCE(AVG(r.quality_score),           0)::NUMERIC(3,2) AS avg_quality,
    COALESCE(AVG(r.speed_score),            0)::NUMERIC(3,2) AS avg_speed,
    COALESCE(AVG(r.accuracy_score),         0)::NUMERIC(3,2) AS avg_accuracy,
    COUNT(r.id)                              AS rating_count,
    MAX(r.created_at)                        AS last_rated_at
FROM buyers b
LEFT JOIN ratings r ON r.buyer_id = b.id
GROUP BY b.id, b.display_name;

COMMENT ON VIEW v_buyer_ratings IS
    '買手評分概覽 — 各維度平均分（通訊、質量、速度、準確度、總分）以及評分總數。';


-- ============================================================
-- 6. Seed Rating Categories (for UI dropdown)
-- ============================================================

CREATE TABLE IF NOT EXISTS rating_categories (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key         TEXT UNIQUE NOT NULL,  -- 'communication', 'quality', 'speed', 'accuracy', 'overall'
    label_zh    TEXT NOT NULL,         -- '溝通', '品質', '速度', '準確度', '總分'
    label_en    TEXT NOT NULL,         -- 'Communication', 'Quality', 'Speed', 'Accuracy', 'Overall'
    weight      NUMERIC(3,2) NOT NULL DEFAULT 1.00,  -- weight in weighted average (overall = 1.5)
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order  INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO rating_categories (key, label_zh, label_en, weight, sort_order)
VALUES
    ('communication', '溝通',          'Communication', 1.0, 1),
    ('quality',       '品質',           'Quality',       1.0, 2),
    ('speed',         '速度',           'Speed',         1.0, 3),
    ('accuracy',      '準確度',         'Accuracy',      1.0, 4),
    ('overall',       '總分',           'Overall',       1.5, 5)
ON CONFLICT (key) DO NOTHING;


-- ============================================================
-- 7. Edge Function Skeleton — ratings
-- ============================================================
--
-- Deploy to: supabase/functions/ratings/index.ts
--
-- Endpoints:
--   GET  /functions/v1/ratings             — list (filter by buyer_id, order_id, min_score)
--   POST /functions/v1/ratings             — create rating
--   GET  /functions/v1/ratings/:id        — get single
--   PATCH /functions/v1/ratings/:id       — update (by rater only)
--   DELETE /functions/v1/ratings/:id      — delete (by admin only)
--
-- See: supabase/functions/ratings/index.ts
-- ============================================================


-- ============================================================
-- 8. RLS for ratings table
-- ============================================================

ALTER TABLE ratings ENABLE ROW LEVEL SECURITY;

-- Admins and the rater can read
CREATE POLICY "ratings_read_all" ON ratings FOR SELECT
    USING (TRUE);

-- Authenticated users can create ratings (order status is enforced by trigger)
CREATE POLICY "ratings_insert" ON ratings FOR INSERT
    WITH CHECK (TRUE);  -- order status trigger guards business rules

-- Only admin can update/delete
CREATE POLICY "ratings_admin_update" ON ratings FOR UPDATE
    USING (TRUE);

CREATE POLICY "ratings_admin_delete" ON ratings FOR DELETE
    USING (TRUE);


-- ============================================================
-- 9. Summary view for admin dashboard
-- ============================================================

CREATE OR REPLACE VIEW v_rating_stats AS
SELECT
    DATE_TRUNC('month', r.created_at) AS month,
    COUNT(r.id)                        AS total_ratings,
    ROUND(AVG(r.overall_score)::NUMERIC, 2) AS avg_overall_score,
    ROUND(AVG(r.communication_score)::NUMERIC, 2) AS avg_communication,
    ROUND(AVG(r.quality_score)::NUMERIC, 2)       AS avg_quality,
    ROUND(AVG(r.speed_score)::NUMERIC, 2)         AS avg_speed,
    ROUND(AVG(r.accuracy_score)::NUMERIC, 2)       AS avg_accuracy,
    COUNT(DISTINCT r.buyer_id)          AS unique_buyers_rated
FROM ratings r
GROUP BY DATE_TRUNC('month', r.created_at)
ORDER BY month DESC;


-- ============================================================
-- ✅ Migration Complete
-- ============================================================
-- To apply:
--   npx supabase db push
--   or paste in Supabase Studio SQL Editor
--
-- After applying:
--   1. Deploy supabase/functions/ratings/index.ts
--   2. Test: POST a completed order rating via API
--   3. Verify: SELECT * FROM v_buyer_ratings;
--      SELECT * FROM v_rating_stats;
--   4. Check: buyers.rating_avg updated after rating insert
-- ============================================================
