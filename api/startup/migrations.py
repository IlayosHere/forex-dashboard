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


def migrate_drop_signals_fk() -> None:
    """Drop the FK constraint from trades.signal_id (idempotent)."""
    from sqlalchemy import text
    from api.db import SessionLocal
    db = SessionLocal()
    try:
        result = db.execute(text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = 'trades_signal_id_fkey' "
            "AND table_name = 'trades'"
        )).fetchone()
        if result:
            db.execute(text(
                "ALTER TABLE trades DROP CONSTRAINT trades_signal_id_fkey"
            ))
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def migrate_add_life_entries_table() -> None:
    """Create life_entries table if it does not exist yet."""
    inspector = inspect(engine)
    if "life_entries" in inspector.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS life_entries ("
            "  id VARCHAR PRIMARY KEY,"
            "  owner VARCHAR NOT NULL,"
            "  body TEXT NOT NULL,"
            "  mood VARCHAR,"
            "  tags JSON NOT NULL DEFAULT '[]',"
            "  entry_at DATETIME NOT NULL,"
            "  created_at DATETIME NOT NULL,"
            "  updated_at DATETIME NOT NULL"
            ")"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_life_entries_owner ON life_entries (owner)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_life_entries_owner_entry_at"
            " ON life_entries (owner, entry_at)"
        ))
    logger.info("Created table life_entries")


def migrate_add_premarket_plans_table() -> None:
    """Create premarket_plans table if it does not exist yet."""
    inspector = inspect(engine)
    if "premarket_plans" in inspector.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS premarket_plans ("
            "  id VARCHAR PRIMARY KEY,"
            "  owner VARCHAR NOT NULL,"
            "  date DATE NOT NULL,"
            "  weekly_dealing_range VARCHAR,"
            "  weekly_dol VARCHAR,"
            "  weekly_opening_gap VARCHAR,"
            "  daily_bias VARCHAR,"
            "  daily_bias_signals JSON NOT NULL,"
            "  h4_pd_array VARCHAR,"
            "  h4_pd_location VARCHAR,"
            "  h1_zone VARCHAR,"
            "  h1_structure VARCHAR,"
            "  ltf_notes VARCHAR,"
            "  narrative VARCHAR NOT NULL,"
            "  checkpoints JSON NOT NULL,"
            "  created_at DATETIME NOT NULL,"
            "  updated_at DATETIME NOT NULL"
            ")"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_premarket_plans_owner ON premarket_plans (owner)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_premarket_plans_owner_date ON premarket_plans (owner, date)"
        ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_premarket_plan_owner_date ON premarket_plans (owner, date)"
        ))
    logger.info("Created table premarket_plans")


def migrate_add_plan_scenarios_table() -> None:
    """Create plan_scenarios table if it does not exist yet."""
    inspector = inspect(engine)
    if "plan_scenarios" in inspector.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS plan_scenarios ("
            "  id VARCHAR PRIMARY KEY,"
            "  plan_id VARCHAR NOT NULL REFERENCES premarket_plans(id) ON DELETE CASCADE,"
            "  reaction_setup_type VARCHAR,"
            "  reaction_setup_detail VARCHAR,"
            "  target_level_type VARCHAR,"
            "  target_level_detail VARCHAR,"
            "  notes VARCHAR NOT NULL,"
            "  outcome_status VARCHAR,"
            "  created_at DATETIME NOT NULL,"
            "  updated_at DATETIME NOT NULL"
            ")"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_plan_scenarios_plan_id ON plan_scenarios (plan_id)"
        ))
    logger.info("Created table plan_scenarios")


def migrate_add_plan_reviews_table() -> None:
    """Create plan_reviews table if it does not exist yet."""
    inspector = inspect(engine)
    if "plan_reviews" in inspector.get_table_names():
        return
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS plan_reviews ("
            "  id VARCHAR PRIMARY KEY,"
            "  plan_id VARCHAR NOT NULL UNIQUE REFERENCES premarket_plans(id) ON DELETE CASCADE,"
            "  bias_correct VARCHAR,"
            "  execution_grade VARCHAR,"
            "  emotion_tags JSON NOT NULL,"
            "  review_notes VARCHAR NOT NULL,"
            "  created_at DATETIME NOT NULL,"
            "  updated_at DATETIME NOT NULL"
            ")"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_plan_reviews_plan_id ON plan_reviews (plan_id)"
        ))
    logger.info("Created table plan_reviews")


def migrate_add_trades_scenario_id_column() -> None:
    """Add scenario_id column to trades table if it does not exist yet.

    No FK constraint — mirrors signal_id (see migrate_drop_signals_fk). Safe to run at
    startup today since this branch has never deployed; once it ships, this specific
    ALTER must be pre-applied manually on prod first (see CLAUDE.md migration-safety rule).
    """
    inspector = inspect(engine)
    if "trades" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("trades")}
    if "scenario_id" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE trades ADD COLUMN scenario_id VARCHAR"))
    logger.info("Added scenario_id column to trades")


def migrate_add_trade_location_column() -> None:
    """Add trade_location column to trades table if it does not exist yet.

    Values: 'home' | 'phone' | 'pc_outside' — nullable (None for backtest/legacy trades).
    Safe at startup for new installs. On prod, pre-apply the ALTER manually via
    /prod-connect before deploying (see CLAUDE.md §Production Migration Safety).
    """
    inspector = inspect(engine)
    if "trades" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("trades")}
    if "trade_location" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE trades ADD COLUMN trade_location VARCHAR"))
    logger.info("Added trade_location column to trades")


def migrate_add_holding_time_minutes_column() -> None:
    """Add holding_time_minutes column to trades table if it does not exist yet.

    Nullable integer — the trader manually logs how many minutes they held the trade.
    On prod Postgres, pre-apply the ALTER manually via /prod-connect before deploying
    (see CLAUDE.md §Production Migration Safety).
    """
    inspector = inspect(engine)
    if "trades" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("trades")}
    if "holding_time_minutes" in columns:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE trades ADD COLUMN holding_time_minutes INTEGER"))
    logger.info("Added holding_time_minutes column to trades")


def run_all() -> None:
    """Run all migrations in order. Called once at startup."""
    migrate_drop_signals_fk()
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
    migrate_add_life_entries_table()
    migrate_add_premarket_plans_table()
    migrate_add_plan_scenarios_table()
    migrate_add_plan_reviews_table()
    migrate_add_trades_scenario_id_column()
    migrate_add_trade_location_column()
    migrate_add_holding_time_minutes_column()
