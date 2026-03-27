"""
api/main.py
-----------
FastAPI application entry point.

Startup creates all DB tables (idempotent via create_all).
CORS is restricted to localhost:3000 (Next.js dev server).
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import Base, engine
from api.routes.calculate import router as calculate_router
from api.routes.signals import router as signals_router
from api.routes.trades import router as trades_router

_raw_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _raw_origins.split(",")]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    Base.metadata.create_all(bind=engine)
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
