-- 010_be_outcome.sql
-- Adds be_outcome column to trades table.
-- Records whether a breakeven stop prevented a loss or cut off a valid TP.
-- Values: 'prevented_loss' | 'missed_tp' | NULL (not yet reviewed)
-- Applies to any trade with outcome = 'breakeven', regardless of instrument type.

ALTER TABLE trades ADD COLUMN be_outcome TEXT DEFAULT NULL;
