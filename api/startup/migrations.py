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


def run_all() -> None:
    """Run all migrations in order. Called once at startup."""
    migrate_add_account_id_column()
    migrate_add_account_balance_columns()
    migrate_add_users_table()
    migrate_add_owner_to_accounts()
    migrate_add_owner_to_trades()
