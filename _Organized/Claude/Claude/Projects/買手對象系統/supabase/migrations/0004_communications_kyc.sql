-- Migration: 0004_communications_kyc.sql
-- BuyerOS — 通訊記錄 + KYC 文件管理
-- Created for P3.3 — 通訊系統 + KYC Management
-- Apply AFTER 0003_rls_and_audit.sql

BEGIN;

-- ─────────────────────────────────────────────────────────────────────────────
-- 1. 通訊記錄表 (communications)
-- 記錄所有來自客戶、買手、客服的來往記錄
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS communications (
  id           UUID        NOT NULL DEFAULT gen_random_uuid(),
  customer_id  UUID        REFERENCES customers(id) ON DELETE SET NULL,
  buyer_id     UUID        REFERENCES buyers(id) ON DELETE SET NULL,
  order_id     UUID        REFERENCES orders(id) ON DELETE SET NULL,

  -- 渠道與方向
  channel      TEXT        NOT NULL CHECK (channel IN (
    'telegram', 'whatsapp', 'email', 'phone', 'sms', 'web', 'in_person'
  )),
  direction    TEXT        NOT NULL CHECK (direction IN ('inbound', 'outbound')),

  -- 內容
  subject      TEXT,
  content      TEXT        NOT NULL,

  -- 平台特定字段
  telegram_message_id  BIGINT,
  telegram_chat_id    BIGINT,
  whatsapp_wa_id      TEXT,
  whatsapp_from       TEXT,

  -- 標籤（用於分類）
  tags         TEXT[]      NOT NULL DEFAULT '{}',

  -- 附件（Storage path 列表）
  attachments  TEXT[]      NOT NULL DEFAULT '{}',

  -- 閱讀與封存狀態
  is_read      BOOLEAN    NOT NULL DEFAULT false,
  is_archived  BOOLEAN    NOT NULL DEFAULT false,

  -- 內部備註（對客戶不可見）
  internal_notes TEXT,

  -- 軟刪除
  deleted_at   TIMESTAMPTZ,

  -- 元數據
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by   TEXT,

  PRIMARY KEY (id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_communications_customer_id ON communications(customer_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_communications_buyer_id    ON communications(buyer_id)    WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_communications_order_id     ON communications(order_id)     WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_communications_channel       ON communications(channel);
CREATE INDEX IF NOT EXISTS idx_communications_direction    ON communications(direction);
CREATE INDEX IF NOT EXISTS idx_communications_is_archived ON communications(is_archived) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_communications_created_at    ON communications(created_at DESC) WHERE deleted_at IS NULL;
-- Tag filter (GIN index for Postgres array)
CREATE INDEX IF NOT EXISTS idx_communications_tags         ON communications USING GIN(tags);

-- updated_at 自動更新
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TRIGGER communications_updated_at
  BEFORE UPDATE ON communications
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE communications IS 'All inbound/outbound communications across channels';

-- ─────────────────────────────────────────────────────────────────────────────
-- 2. 買手 KYC 文件表 (buyer_documents)
-- 存放買手身份證明文件（身份證、地址證明等）的 Supabase Storage 路徑
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS buyer_documents (
  id           UUID        NOT NULL DEFAULT gen_random_uuid(),
  buyer_id     UUID        NOT NULL REFERENCES buyers(id) ON DELETE CASCADE,

  document_type TEXT        NOT NULL CHECK (document_type IN (
    'hkid_front',       -- 香港身份證正面
    'hkid_back',        -- 香港身份證背面
    'passport',         -- 護照
    'address_proof',    -- 地址證明（水電煤單）
    'bank_card_front',  -- 銀行卡正面
    'bank_card_back',   -- 銀行卡背面
    'company_cert',      -- 公司商業登記
    'other'             -- 其他文件
  )),

  -- Storage bucket + path
  storage_bucket TEXT        NOT NULL DEFAULT 'buyer-documents',
  storage_path   TEXT        NOT NULL,

  -- 文件元數據
  original_filename TEXT,
  file_size_bytes   BIGINT,
  mime_type         TEXT,

  -- 審核狀態
  verification_status TEXT  NOT NULL DEFAULT 'pending'
    CHECK (verification_status IN ('pending', 'approved', 'rejected')),
  verified_at       TIMESTAMPTZ,
  verified_by       TEXT,
  rejection_reason  TEXT,

  -- 軟刪除
  deleted_at        TIMESTAMPTZ,

  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

  PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS idx_buyer_documents_buyer_id   ON buyer_documents(buyer_id);
CREATE INDEX IF NOT EXISTS idx_buyer_documents_doc_type  ON buyer_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_buyer_documents_status     ON buyer_documents(verification_status);
CREATE INDEX IF NOT EXISTS idx_buyer_documents_buyer_status ON buyer_documents(buyer_id, verification_status);

CREATE TRIGGER buyer_documents_updated_at
  BEFORE UPDATE ON buyer_documents
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

COMMENT ON TABLE buyer_documents IS 'KYC documents for buyers (ID cards, address proof, bank cards, etc.)';

-- ─────────────────────────────────────────────────────────────────────────────
-- 3. Supabase Storage Buckets（需在 Dashboard 或 CLI 建立）
-- ─────────────────────────────────────────────────────────────────────────────

-- 注意：Storage buckets 需手動創建（Supabase CLI 不支持 storage.bucket 創建）：
--   1. 登入 Supabase Dashboard → Storage → New bucket
--   2. 或使用 CLI：
--      supabase storage create-bucket buyer-documents --no-public

-- 建議權限策略（RLS）：
--   INSERT/UPDATE/DELETE: 僅管理員角色
--   SELECT: 管理員 + 對應 buyer_id 的買手本人

COMMENT ON COLUMN buyer_documents.storage_path IS
  'Format: buyers/{buyer_id}/{document_type}_{timestamp}.{ext}
   Example: buyers/abc123/hkid_front_20260501.png';

COMMIT;

-- ─────────────────────────────────────────────────────────────────────────────
-- Rollback (if needed):
-- DROP TABLE IF EXISTS buyer_documents;
-- DROP TABLE IF EXISTS communications;
-- DROP FUNCTION IF EXISTS update_updated_at_column;
-- ─────────────────────────────────────────────────────────────────────────────
