"""
api/startup/migrations.py
--------------------------
Lightweight schema migrations run at startup before the app accepts requests.

SQLAlchemy's create_all only creates new tables — it won't ALTER existing ones.
Each function is idempotent: it inspects current columns before running DDL.
"""
from __future__ import annotations

import logging

from sqlalchemy import inspect, text

from api.db import engine

logger = logging.getLogger(__name__)


def migrate_add_account_id_column() -> None:
    """Add account_id column to trades table if it does not exist yet."""
    inspector = inspect(engine)
    if "trades" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("trades")}
    if "account_id" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE trades ADD COLUMN account_id VARCHAR REFERENCES accounts(id) ON DELETE RESTRICT"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_trades_account_id ON trades (account_id)"))


def migrate_add_account_balance_columns() -> None:
    """Add balance column to accounts table if it does not exist yet."""
    inspector = inspect(engine)
    if "accounts" not in inspector.get_table_names():
        return
    cols = [c["name"] for c in inspector.get_columns("accounts")]
    if "balance" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE accounts ADD COLUMN balance FLOAT"))


def migrate_add_users_table() -> None:
    """Create the users table if it does not exist yet."""
    inspector = inspect(engine)
    if "users" in inspector.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS users ("
            "  id VARCHAR PRIMARY KEY,"
            "  username VARCHAR NOT NULL UNIQUE,"
            "  password_hash VARCHAR NOT NULL,"
            "  is_admin BOOLEAN NOT NULL DEFAULT 0,"
            "  created_at DATETIME NOT NULL"
            ")"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"
        ))


def migrate_add_owner_to_accounts() -> None:
    """Add owner column to accounts table if it does not exist yet."""
    inspector = inspect(engine)
    if "accounts" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("accounts")}
    if "owner" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE accounts ADD COLUMN owner VARCHAR NOT NULL DEFAULT 'admin'"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_accounts_owner ON accounts (owner)"
        ))


def migrate_add_owner_to_trades() -> None:
    """Add owner column to trades table if it does not exist yet."""
    inspector = inspect(engine)
    if "trades" not in inspector.get_table_names():
        return
    cols = {c["name"] for c in inspector.get_columns("trades")}
    if "owner" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE trades ADD COLUMN owner VARCHAR NOT NULL DEFAULT 'admin'"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_trades_owner ON trades (owner)"
        ))


def migrate_add_trade_owner_open_time_index() -> None:
    """Create composite index ix_trades_owner_open_time on trades (owner, open_time) if absent."""
    inspector = inspect(engine)
    if "trades" not in inspector.get_table_names():
        return
    existing = {idx["name"] for idx in inspector.get_indexes("trades")}
    if "ix_trades_owner_open_time" in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_trades_owner_open_time ON trades (owner, open_time)"
        ))
    logger.info("Created index ix_trades_owner_open_time")


def migrate_add_trade_owner_status_index() -> None:
    """Create composite index ix_trades_owner_status on trades (owner, status) if absent."""
    inspector = inspect(engine)
    if "trades" not in inspector.get_table_names():
        return
    existing = {idx["name"] for idx in inspector.get_indexes("trades")}
    if "ix_trades_owner_status" in existing:
        return
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_trades_owner_status ON trades (owner, status)"
        ))
    logger.info("Created index ix_trades_owner_status")


def migrate_add_rule_categories_table() -> None:
    """Create rule_categories table if it does not exist yet."""
    inspector = inspect(engine)
    if "rule_categories" in inspector.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS rule_categories ("
            "  id VARCHAR PRIMARY KEY,"
            "  owner VARCHAR NOT NULL,"
            "  name VARCHAR(100) NOT NULL,"
            "  created_at DATETIME NOT NULL"
            ")"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_rule_categories_owner"
            " ON rule_categories (owner)"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_rule_category_owner_name"
            " ON rule_categories (owner, name)"
        ))
    logger.info("Created table rule_categories")


def migrate_add_rules_table() -> None:
    """Create rules table if it does not exist yet."""
    inspector = inspect(engine)
    if "rules" in inspector.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS rules ("
            "  id VARCHAR PRIMARY KEY,"
            "  owner VARCHAR NOT NULL,"
            "  title VARCHAR(80) NOT NULL,"
            "  body TEXT,"
            "  category_id VARCHAR REFERENCES rule_categories(id) ON DELETE SET NULL,"
            "  break_count INTEGER NOT NULL DEFAULT 0,"
            "  created_at DATETIME NOT NULL,"
            "  updated_at DATETIME NOT NULL"
            ")"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_rules_owner ON rules (owner)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_rules_category_id ON rules (category_id)"
        ))
    logger.info("Created table rules")


def migrate_add_rule_mistake_links_table() -> None:
    """Create rule_mistake_links table if it does not exist yet."""
    inspector = inspect(engine)
    if "rule_mistake_links" in inspector.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS rule_mistake_links ("
            "  rule_id VARCHAR NOT NULL REFERENCES rules(id) ON DELETE CASCADE,"
            "  mistake_id VARCHAR NOT NULL REFERENCES mistakes(id) ON DELETE CASCADE,"
            "  linked_at DATETIME NOT NULL,"
            "  PRIMARY KEY (rule_id, mistake_id)"
            ")"
        ))
    logger.info("Created table rule_mistake_links")


def migrate_gates_grades_experiments() -> None:
    """Create gate_sets, grade_thresholds, experiments tables and add gate/grade columns to signals."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    with engine.begin() as conn:
        if "gate_sets" not in tables:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS gate_sets ("
                "  id VARCHAR PRIMARY KEY,"
                "  owner VARCHAR NOT NULL DEFAULT 'admin',"
                "  strategy VARCHAR NOT NULL,"
                "  name VARCHAR(80) NOT NULL,"
                "  description TEXT,"
                "  is_active INTEGER NOT NULL DEFAULT 0,"
                "  conditions TEXT NOT NULL DEFAULT '[]',"
                "  created_at DATETIME NOT NULL,"
                "  updated_at DATETIME NOT NULL"
                ")"
            ))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_gate_sets_owner_strategy ON gate_sets (owner, strategy)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_gate_sets_strategy_active ON gate_sets (strategy, is_active)"))
            logger.info("Created table gate_sets")

        if "grade_thresholds" not in tables:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS grade_thresholds ("
                "  id VARCHAR PRIMARY KEY,"
                "  owner VARCHAR NOT NULL DEFAULT 'admin',"
                "  strategy VARCHAR NOT NULL,"
                "  a_min INTEGER NOT NULL DEFAULT 60,"
                "  b_min INTEGER NOT NULL DEFAULT 20,"
                "  is_active INTEGER NOT NULL DEFAULT 1,"
                "  created_at DATETIME NOT NULL"
                ")"
            ))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_grade_thresholds_strategy_active ON grade_thresholds (strategy, is_active)"))
            logger.info("Created table grade_thresholds")

        if "experiments" not in tables:
            conn.execute(text(
                "CREATE TABLE IF NOT EXISTS experiments ("
                "  id VARCHAR PRIMARY KEY,"
                "  owner VARCHAR NOT NULL DEFAULT 'admin',"
                "  name VARCHAR(120) NOT NULL,"
                "  strategy VARCHAR NOT NULL,"
                "  conditions TEXT NOT NULL DEFAULT '[]',"
                "  date_from DATETIME,"
                "  date_to DATETIME,"
                "  notes TEXT,"
                "  last_run_at DATETIME,"
                "  last_summary TEXT,"
                "  created_at DATETIME NOT NULL,"
                "  updated_at DATETIME NOT NULL"
                ")"
            ))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_experiments_owner_strategy ON experiments (owner, strategy)"))
            logger.info("Created table experiments")

    if "signals" in tables:
        signal_cols = {c["name"] for c in inspector.get_columns("signals")}
        with engine.begin() as conn:
            if "gate_status" not in signal_cols:
                conn.execute(text("ALTER TABLE signals ADD COLUMN gate_status VARCHAR NOT NULL DEFAULT 'no_gates'"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_signals_gate_status ON signals (gate_status)"))
            if "gate_block_reason" not in signal_cols:
                conn.execute(text("ALTER TABLE signals ADD COLUMN gate_block_reason VARCHAR"))
            if "gate_set_id" not in signal_cols:
                conn.execute(text("ALTER TABLE signals ADD COLUMN gate_set_id VARCHAR"))
            if "grade" not in signal_cols:
                conn.execute(text("ALTER TABLE signals ADD COLUMN grade VARCHAR"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_signals_grade ON signals (grade)"))
            if "score_snapshot" not in signal_cols:
                conn.execute(text("ALTER TABLE signals ADD COLUMN score_snapshot INTEGER"))
            if "score_max_snapshot" not in signal_cols:
                conn.execute(text("ALTER TABLE signals ADD COLUMN score_max_snapshot INTEGER"))
        logger.info("Migration 012: gate/grade columns added to signals")


def run_all() -> None:
    """Run all migrations in order. Called once at startup."""
    migrate_add_account_id_column()
    migrate_add_account_balance_columns()
    migrate_add_users_table()
    migrate_add_owner_to_accounts()
    migrate_add_owner_to_trades()
    migrate_add_trade_owner_open_time_index()
    migrate_add_trade_owner_status_index()
    migrate_add_rule_categories_table()
    migrate_add_rules_table()
    migrate_add_rule_mistake_links_table()
    migrate_gates_grades_experiments()
