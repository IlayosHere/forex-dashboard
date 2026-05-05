-- Migration 007: add ict_ifvg_bars to trades
-- Tracks how many bars elapsed between FVG formation and IFVG trigger.
-- Integer, nullable (MNQ trades only). 1 = filled on the very next bar.

ALTER TABLE trades ADD COLUMN ict_ifvg_bars INTEGER;
