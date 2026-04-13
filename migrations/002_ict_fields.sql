-- Migration 002: ICT trade fields for MNQ journaling
-- Adds 6 ICT-specific columns to the trades table.
-- All columns are nullable — existing forex trades are unaffected.
--
-- Run this against signals.db (or the production PostgreSQL database)
-- BEFORE deploying the code that references these columns.

ALTER TABLE trades ADD COLUMN ict_setup_type TEXT;
ALTER TABLE trades ADD COLUMN ict_setup_detail TEXT;
ALTER TABLE trades ADD COLUMN ict_tp_target TEXT;
ALTER TABLE trades ADD COLUMN ict_ifvg_timeframe TEXT;
ALTER TABLE trades ADD COLUMN ict_smt_present BOOLEAN;
ALTER TABLE trades ADD COLUMN ict_tdo_aligned BOOLEAN;
