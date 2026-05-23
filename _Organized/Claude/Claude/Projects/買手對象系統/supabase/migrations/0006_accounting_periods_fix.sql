-- ============================================================
-- Migration: 0006_accounting_periods_fix.sql
-- ============================================================
-- Problem: 0001_initial_reconstructed.sql defines accounting_periods
-- with columns (period, opened_at, opened_by, notes) that 0002
-- omits when recreating the table via CREATE TABLE IF NOT EXISTS.
-- This migration supplements the missing columns idempotently.
--
-- Also syncs existing period_name values into the new period column
-- to ensure consistency as the unified identifier key.
-- ============================================================

-- Supplement columns that 0001 has but 0002 lacks
ALTER TABLE accounting_periods ADD COLUMN IF NOT EXISTS period TEXT UNIQUE;
ALTER TABLE accounting_periods ADD COLUMN IF NOT EXISTS opened_at TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE accounting_periods ADD COLUMN IF NOT EXISTS opened_by UUID REFERENCES auth.users(id);
ALTER TABLE accounting_periods ADD COLUMN IF NOT EXISTS notes TEXT;

-- Sync period = period_name for all existing rows without a period value
UPDATE accounting_periods
SET period = period_name
WHERE period IS NULL AND period_name IS NOT NULL;
