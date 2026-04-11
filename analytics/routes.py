"""
analytics/routes.py
-------------------
FastAPI router for the analytics engine.

GET /api/analytics/parameters — list registered parameter definitions.
GET /api/analytics/enriched   — resolved signals with derived params.
"""
from __future__ import annotations

import logging
from typing import Annotated

import analytics.params  # noqa: F401 — trigger param registration
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from analytics.candle_cache import CandleCache, get_app_cache
from analytics.enrichment import enrich_batch, fetch_resolved
from analytics.registry import get_params_for_strategy
from analytics.schemas import (
    EnrichedListResponse,
    EnrichedSignalResponse,
    ParamInfo,
    ParamListResponse,
)
from api.auth import get_current_user
from api.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _param_to_info(strategy: str | None) -> list[ParamInfo]:
    """Convert registry ParamDefs to response models."""
    target = strategy or "*"
    params = get_params_for_strategy(target)
    return [
        ParamInfo(
            name=p.name,
            dtype=p.dtype,
            strategies=sorted(p.strategies),
            needs_candles=p.needs_candles,
        )
        for p in params
    ]


@router.get("/parameters", response_model=ParamListResponse)
def list_parameters(
    _user: Annotated[str, Depends(get_current_user)],
    _db: Annotated[Session, Depends(get_db)],
    strategy: str | None = Query(None, description="Filter by strategy slug"),
) -> ParamListResponse:
    """List all registered analytics parameters, optionally filtered by strategy."""
    items = _param_to_info(strategy)
    return ParamListResponse(items=items, total=len(items))


def _to_enriched_response(row: dict) -> EnrichedSignalResponse:
    """Convert an enriched dict to the Pydantic response model."""
    return EnrichedSignalResponse(
        id=row["id"],
        strategy=row["strategy"],
        symbol=row["symbol"],
        direction=row["direction"],
        candle_time=row["candle_time"],
        entry=row["entry"],
        sl=row["sl"],
        tp=row["tp"],
        risk_pips=row["risk_pips"],
        spread_pips=row["spread_pips"],
        resolution=row["resolution"],
        resolution_candles=row["resolution_candles"],
        params=row["params"],
    )


@router.get("/enriched", response_model=EnrichedListResponse)
def list_enriched(
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[CandleCache, Depends(get_app_cache)],
    strategy: str | None = Query(None, description="Filter by strategy slug"),
    symbol: str | None = Query(None, description="Filter by currency pair"),
    limit: int = Query(50, ge=1, le=2000, description="Max results"),
) -> EnrichedListResponse:
    """Return resolved signals enriched with all applicable derived params."""
    signals = fetch_resolved(db, strategy=strategy, symbol=symbol, limit=limit)
    unique_pairs = sorted({(s.symbol, s.strategy) for s in signals})
    cache.warm(unique_pairs)
    enriched = enrich_batch(signals, candle_cache=cache)
    items = [_to_enriched_response(row) for row in enriched]
    return EnrichedListResponse(items=items, total=len(items))
