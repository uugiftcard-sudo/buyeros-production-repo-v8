-- ============================================================
-- Migration: 0008_audit_log_protection.sql
-- ============================================================
-- Ensures audit_log records are immutable once written.
-- Applies after 0003 (which creates the audit_log table and
-- its insert trigger) to add UPDATE/DELETE prevention.
-- Safe to re-apply — uses DROP IF EXISTS before CREATE.
-- ============================================================

-- ─── Prevention Function ────────────────────────────────────
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'Audit log records cannot be modified or deleted';
END;
$$ LANGUAGE plpgsql;

-- ─── Block UPDATE ───────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_prevent_audit_log_update ON audit_log;
CREATE TRIGGER trg_prevent_audit_log_update
  BEFORE UPDATE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();

-- ─── Block DELETE ───────────────────────────────────────────
DROP TRIGGER IF EXISTS trg_prevent_audit_log_delete ON audit_log;
CREATE TRIGGER trg_prevent_audit_log_delete
  BEFORE DELETE ON audit_log
  FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
