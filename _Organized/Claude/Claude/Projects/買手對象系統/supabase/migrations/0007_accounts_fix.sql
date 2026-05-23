-- ============================================================
-- Migration: 0007_accounts_fix.sql
-- ============================================================
-- Problem: 0002_accounting_layer.sql includes is_cash_flow_relevant
-- and tax_category in the accounts table definition, but the original
-- 0001 schema (which 0002 extends) does not have these columns.
-- This migration adds them idempotently so both migration paths
-- converge to the same accounts schema.
-- ============================================================

ALTER TABLE accounts ADD COLUMN IF NOT EXISTS is_cash_flow_relevant BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS tax_category TEXT;
