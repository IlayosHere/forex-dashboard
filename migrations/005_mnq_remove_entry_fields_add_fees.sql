-- Migration 005: Remove entry model/location fields, add broker fees
-- ict_entry_model and ict_pd_array removed — not relevant to this strategy.
-- fees added to track broker commissions per trade.

-- SQLite does not support DROP COLUMN on older versions; existing rows keep
-- the columns as NULL but they are no longer used by the application.
-- On PostgreSQL, drop them explicitly:
--   ALTER TABLE trades DROP COLUMN IF EXISTS ict_entry_model;
--   ALTER TABLE trades DROP COLUMN IF EXISTS ict_pd_array;

ALTER TABLE trades ADD COLUMN IF NOT EXISTS fees REAL;
