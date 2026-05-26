"""
api/main.py
-----------
FastAPI application entry point.

Startup creates all DB tables (idempotent via create_all), runs schema
migrations, and seeds default users and accounts from env vars.
CORS is restricted to CORS_ORIGINS env var (default: localhost:3000).
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from analytics.routes import router as analytics_router
from analytics.routes_stats import router as analytics_stats_router
from api.auth import router as auth_router
from api.db import Base, SessionLocal, engine
import api.models_gates  # noqa: F401 — registers gate/grade/experiment models with Base
from api.routes.accounts import router as accounts_router
from api.routes.auto_gate import router as auto_gate_router
from api.routes.calculate import router as calculate_router
from api.routes.calendar import router as calendar_router
from api.routes.categories import router as categories_router
from api.routes.experiments import router as experiments_router
from api.routes.gates import router as gates_router
from api.routes.grades import router as grades_router
from api.routes.mistakes import router as mistakes_router
from api.routes.rules import router as rules_router
from api.routes.trade_mistakes import router as trade_mistakes_router
from api.routes.sessions import router as sessions_router
from api.routes.signals import router as signals_router
from api.routes.stats import router as stats_router
from api.routes.trades import router as trades_router
from api.startup.migrations import run_all as run_migrations
from api.startup.prewarm import prewarm_loop
from api.startup.seed import seed_default_accounts, seed_users_from_env

load_dotenv()

# Alias kept for test patching compatibility: tests patch api.main._prewarm_loop
_prewarm_loop = prewarm_loop

logger = logging.getLogger(__name__)

_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _raw_origins.split(",")]


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
    run_migrations()
    db = SessionLocal()
    try:
        seed_users_from_env(db)
        seed_default_accounts(db)
    finally:
        db.close()
    logger.info("Startup complete")
    task = asyncio.create_task(_prewarm_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


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
app.include_router(mistakes_router, prefix="/api", tags=["mistakes"])
app.include_router(trade_mistakes_router, prefix="/api", tags=["trade-mistakes"])
app.include_router(calendar_router, prefix="/api")
app.include_router(analytics_router, prefix="/api", tags=["analytics"])
app.include_router(analytics_stats_router, prefix="/api", tags=["analytics"])
app.include_router(sessions_router, prefix="/api", tags=["sessions"])
app.include_router(rules_router, prefix="/api", tags=["rules"])
app.include_router(categories_router, prefix="/api", tags=["rule-categories"])
app.include_router(gates_router, prefix="/api", tags=["gates"])
app.include_router(grades_router, prefix="/api", tags=["grades"])
app.include_router(experiments_router, prefix="/api", tags=["experiments"])
app.include_router(auto_gate_router, prefix="/api", tags=["auto-gate"])
