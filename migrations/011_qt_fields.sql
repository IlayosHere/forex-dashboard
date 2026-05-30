-- Migration 011: Quarterly Theory fields
-- Adds qt_* columns used by the qt-mnq strategy journaling.

ALTER TABLE trades ADD COLUMN qt_fvg_quarter   TEXT DEFAULT NULL;
ALTER TABLE trades ADD COLUMN qt_entry_quarter  TEXT DEFAULT NULL;
ALTER TABLE trades ADD COLUMN qt_fvg_date       TEXT DEFAULT NULL;
ALTER TABLE trades ADD COLUMN qt_fvg_type       TEXT DEFAULT NULL;
ALTER TABLE trades ADD COLUMN qt_entry_type     TEXT DEFAULT NULL;
