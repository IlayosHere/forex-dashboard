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
