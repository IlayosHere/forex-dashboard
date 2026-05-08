-- Migration 009: Trade feelings + session journal
-- Adds per-trade emotional state fields (MNQ only in practice, nullable for all).
-- Creates trading_sessions table for day-level session journaling.

-- Trade feelings
ALTER TABLE trades ADD COLUMN feeling_before TEXT;
ALTER TABLE trades ADD COLUMN feeling_during TEXT;
ALTER TABLE trades ADD COLUMN feeling_after  TEXT;

-- Session journal table (one row per owner+date)
CREATE TABLE IF NOT EXISTS trading_sessions (
    id          TEXT    NOT NULL PRIMARY KEY,
    owner       TEXT    NOT NULL DEFAULT 'admin',
    date        TEXT    NOT NULL,   -- ISO date string: YYYY-MM-DD
    had_pre_session_plan  INTEGER,  -- 1 = yes, 0 = no, NULL = not logged
    feeling_pre  TEXT,
    feeling_during TEXT,
    feeling_post TEXT,
    session_notes TEXT NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,

    CONSTRAINT uq_session_owner_date UNIQUE (owner, date)
);

CREATE INDEX IF NOT EXISTS ix_trading_sessions_owner       ON trading_sessions (owner);
CREATE INDEX IF NOT EXISTS ix_trading_sessions_owner_date  ON trading_sessions (owner, date);
