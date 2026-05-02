-- 006_rule_compliance.sql
-- Adds rule_followed column to trades and creates trade_mistakes join table.
--
-- rule_followed: NULL = not reviewed, TRUE = followed rules, FALSE = had mistake(s)
-- trade_mistakes: many-to-many join between trades and mistakes

-- SQLite and PostgreSQL compatible
ALTER TABLE trades ADD COLUMN rule_followed BOOLEAN;

CREATE TABLE IF NOT EXISTS trade_mistakes (
    trade_id   TEXT NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
    mistake_id TEXT NOT NULL REFERENCES mistakes(id) ON DELETE CASCADE,
    linked_at  DATETIME NOT NULL,
    PRIMARY KEY (trade_id, mistake_id)
);

CREATE INDEX IF NOT EXISTS ix_trade_mistakes_trade_id   ON trade_mistakes(trade_id);
CREATE INDEX IF NOT EXISTS ix_trade_mistakes_mistake_id ON trade_mistakes(mistake_id);
