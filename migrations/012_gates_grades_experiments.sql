-- Migration 012: Gates, Grades, and Experiments system
-- Adds:
--   - gate_sets table: named condition sets for live signal filtering
--   - grade_thresholds table: per-strategy A/B/C/D score cutoffs
--   - experiments table: saved historical backtest definitions
--   - gate_status, gate_block_reason, gate_set_id columns on signals
--   - grade, score_snapshot, score_max_snapshot columns on signals

-- Gate sets
CREATE TABLE IF NOT EXISTS gate_sets (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL DEFAULT 'admin',
    strategy TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    is_active INTEGER NOT NULL DEFAULT 0,
    conditions TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_gate_sets_owner_strategy ON gate_sets (owner, strategy);
CREATE INDEX IF NOT EXISTS ix_gate_sets_strategy_active ON gate_sets (strategy, is_active);

-- Grade thresholds
CREATE TABLE IF NOT EXISTS grade_thresholds (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL DEFAULT 'admin',
    strategy TEXT NOT NULL,
    a_min INTEGER NOT NULL DEFAULT 60,
    b_min INTEGER NOT NULL DEFAULT 20,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_grade_thresholds_strategy_active ON grade_thresholds (strategy, is_active);

-- Experiments
CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    owner TEXT NOT NULL DEFAULT 'admin',
    name TEXT NOT NULL,
    strategy TEXT NOT NULL,
    conditions TEXT NOT NULL DEFAULT '[]',
    date_from TEXT,
    date_to TEXT,
    notes TEXT,
    last_run_at TEXT,
    last_summary TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_experiments_owner_strategy ON experiments (owner, strategy);

-- New columns on signals table
ALTER TABLE signals ADD COLUMN gate_status TEXT NOT NULL DEFAULT 'no_gates';
ALTER TABLE signals ADD COLUMN gate_block_reason TEXT;
ALTER TABLE signals ADD COLUMN gate_set_id TEXT;
ALTER TABLE signals ADD COLUMN grade TEXT;
ALTER TABLE signals ADD COLUMN score_snapshot INTEGER;
ALTER TABLE signals ADD COLUMN score_max_snapshot INTEGER;

CREATE INDEX IF NOT EXISTS ix_signals_gate_status ON signals (gate_status);
CREATE INDEX IF NOT EXISTS ix_signals_grade ON signals (grade);
