"""
api/main.py
-----------
FastAPI application entry point.

Startup creates all DB tables (idempotent via create_all) and seeds default
accounts. CORS is restricted to localhost:3000 (Next.js dev server).
"""
from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
load_dotenv()
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from api.db import Base, SessionLocal, engine
from api.models import AccountModel, UserModel
from api.auth import router as auth_router
from api.routes.accounts import router as accounts_router
from api.routes.calculate import router as calculate_router
from api.routes.signals import router as signals_router
from api.routes.stats import router as stats_router
from api.routes.trades import router as trades_router

logger = logging.getLogger(__name__)

_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _raw_origins.split(",")]


def _migrate_add_account_id_column() -> None:
    """Add account_id column to trades table if it does not exist yet.

    SQLAlchemy's create_all only creates new tables — it won't alter existing
    ones. This lightweight migration covers the schema change without Alembic.
    """
    inspector = inspect(engine)
    if "trades" not in inspector.get_table_names():
        return  # Table doesn't exist yet; create_all will handle it
    columns = {col["name"] for col in inspector.get_columns("trades")}
    if "account_id" in columns:
        return  # Already migrated
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE trades ADD COLUMN account_id VARCHAR REFERENCES accounts(id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_trades_account_id ON trades (account_id)"))


def _migrate_add_account_balance_columns() -> None:
    inspector = inspect(engine)
    if "accounts" not in inspector.get_table_names():
        return
    cols = [c["name"] for c in inspector.get_columns("accounts")]
    with engine.begin() as conn:
        if "balance" not in cols:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN balance FLOAT"))


def _migrate_add_users_table() -> None:
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


def _migrate_add_owner_to_accounts() -> None:
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


def _migrate_add_owner_to_trades() -> None:
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


def seed_default_accounts(db: Session) -> None:
    """Create default accounts for each user that has none."""
    users = db.scalars(select(UserModel)).all()
    now = datetime.now(timezone.utc)
    defaults = [
        ("Demo", "demo", "forex"),
        ("Live", "live", "forex"),
        ("Demo", "demo", "futures_mnq"),
        ("Live", "live", "futures_mnq"),
    ]
    for user in users:
        user_count = db.scalar(
            select(func.count())
            .select_from(AccountModel)
            .where(AccountModel.owner == user.username),
        )
        if user_count and user_count > 0:
            continue
        for name, acct_type, inst_type in defaults:
            db.add(AccountModel(
                id=str(uuid.uuid4()),
                name=name,
                account_type=acct_type,
                instrument_type=inst_type,
                status="active",
                prop_firm=None,
                phase=None,
                owner=user.username,
                created_at=now,
            ))
        logger.info("Seeded default accounts for user %r", user.username)
    db.commit()


def seed_users_from_env(db: Session) -> str:
    """Import AUTH_USERS env var into the users table on first boot. Idempotent.

    Returns the first username found in env vars, or "admin" as fallback.
    """
    import json as _json
    import uuid as _uuid
    raw = os.getenv("AUTH_USERS", "")
    if not raw:
        username = os.getenv("AUTH_USERNAME", "")
        pw_hash = os.getenv("AUTH_PASSWORD_HASH", "")
        env_users = {username: pw_hash} if username and pw_hash else {}
    else:
        try:
            env_users = _json.loads(raw)
        except Exception:
            logger.warning("AUTH_USERS env var is malformed JSON — skipping user seed")
            return "admin"

    if not env_users:
        logger.warning("No users found in AUTH_USERS or AUTH_USERNAME — no users seeded")
        return "admin"

    first_username = next(iter(env_users))
    now = datetime.now(timezone.utc)
    for username, pw_hash in env_users.items():
        exists = db.scalar(select(UserModel).where(UserModel.username == username))
        if exists is None:
            db.add(UserModel(
                id=str(_uuid.uuid4()),
                username=username,
                password_hash=pw_hash,
                is_admin=True,
                created_at=now,
            ))
            logger.info("Seeded user %r from env var", username)
        elif exists.password_hash != pw_hash:
            exists.password_hash = pw_hash
            logger.info("Updated password hash for user %r", username)
    db.commit()
    return first_username


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create tables, run migrations, seed defaults on startup."""
    jwt_secret = os.getenv("JWT_SECRET", "")
    if not jwt_secret or len(jwt_secret) < 32:
        raise RuntimeError(
            "JWT_SECRET env var is required and must be at least 32 characters. "
            "Generate one with: openssl rand -hex 32"
        )
    logger.info("Starting up: creating tables and running migrations")
    Base.metadata.create_all(bind=engine)
    _migrate_add_account_id_column()
    _migrate_add_account_balance_columns()
    _migrate_add_users_table()
    _migrate_add_owner_to_accounts()
    _migrate_add_owner_to_trades()
    db = SessionLocal()
    try:
        seed_users_from_env(db)
        seed_default_accounts(db)
    finally:
        db.close()
    logger.info("Startup complete")
    yield


app = FastAPI(
    title="Forex Signal Dashboard API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(signals_router, prefix="/api")
app.include_router(calculate_router, prefix="/api")
app.include_router(stats_router, prefix="/api", tags=["stats"])
app.include_router(trades_router, prefix="/api")
app.include_router(accounts_router, prefix="/api", tags=["accounts"])
