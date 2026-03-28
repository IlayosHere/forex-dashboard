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
from api.models import AccountModel
from api.routes.accounts import router as accounts_router
from api.routes.calculate import router as calculate_router
from api.routes.signals import router as signals_router
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


def seed_default_accounts(db: Session) -> None:
    """Create default accounts if none exist."""
    count = db.scalar(select(func.count()).select_from(AccountModel))
    if count and count > 0:
        return

    now = datetime.now(timezone.utc)
    defaults = [
        ("Demo", "demo", "forex"),
        ("Live", "live", "forex"),
        ("Demo", "demo", "futures_mnq"),
        ("Live", "live", "futures_mnq"),
    ]
    for name, acct_type, inst_type in defaults:
        db.add(AccountModel(
            id=str(uuid.uuid4()),
            name=name,
            account_type=acct_type,
            instrument_type=inst_type,
            status="active",
            prop_firm=None,
            phase=None,
            created_at=now,
        ))
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Create tables, run migrations, seed defaults on startup."""
    logger.info("Starting up: creating tables and running migrations")
    Base.metadata.create_all(bind=engine)
    _migrate_add_account_id_column()
    db = SessionLocal()
    try:
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
    allow_headers=["*"],
)

app.include_router(signals_router, prefix="/api")
app.include_router(calculate_router, prefix="/api")
app.include_router(trades_router, prefix="/api")
app.include_router(accounts_router, prefix="/api", tags=["accounts"])
