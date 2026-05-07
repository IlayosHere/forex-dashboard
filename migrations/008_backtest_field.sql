-- Migration 008: add criteria_met_at_entry to trades
-- Anti-hindsight-bias check: did the setup fully qualify at bar close before the move?
-- Nullable boolean; only relevant for backtest account trades.

ALTER TABLE trades ADD COLUMN criteria_met_at_entry BOOLEAN;
