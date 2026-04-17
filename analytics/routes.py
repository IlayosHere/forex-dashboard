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
from analytics.registry import get_all_params, get_params_for_strategy
from analytics.routes_stats import filter_by_symbol, get_enriched
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
    """Convert registry ParamDefs to response models.

    When strategy is None, returns ALL registered params (cross-strategy and
    strategy-specific). When strategy is provided, returns only params that
    apply to that strategy slug.
    """
    params = get_all_params() if strategy is None else get_params_for_strategy(strategy)
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
    strategy: str = Query(..., description="Strategy slug (required)"),
    symbol: str | None = Query(None, description="Filter by currency pair"),
    limit: int = Query(50, ge=1, le=2000, description="Max results"),
) -> EnrichedListResponse:
    """Return resolved signals enriched with all applicable derived params.

    Routes through the shared enriched-signal cache so signal counts are
    consistent with /univariate and /summary for the same strategy.
    Symbol filter and limit are applied as post-cache slices.
    """
    enriched = filter_by_symbol(get_enriched(strategy, db, cache), symbol)
    items = [_to_enriched_response(row) for row in enriched[:limit]]
    return EnrichedListResponse(items=items, total=len(enriched))
