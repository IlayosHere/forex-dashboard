-- Migration 004: Extended ICT fields for MNQ trade journaling
-- Adds 3 new ICT-specific columns to the trades table.
-- All columns are nullable — existing trades are unaffected.
--
-- New columns:
--   ict_htf_bias     TEXT  — aligned / counter / neutral
--   ict_entry_model  TEXT  — silver_bullet / cisd / bms / ote / turtle_soup / other
--   ict_pd_array     TEXT  — premium / discount / equilibrium
--
-- Works on both SQLite (dev) and PostgreSQL (prod).
-- Apply to dev first: python -c "import sqlite3; conn=sqlite3.connect('signals.db'); conn.executescript(open('migrations/004_ict_extended_fields.sql').read()); conn.close()"

ALTER TABLE trades ADD COLUMN ict_htf_bias TEXT;
ALTER TABLE trades ADD COLUMN ict_entry_model TEXT;
ALTER TABLE trades ADD COLUMN ict_pd_array TEXT;
