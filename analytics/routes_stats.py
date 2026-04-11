"""
analytics/routes_stats.py
-------------------------
FastAPI router for analytics statistics endpoints.

GET /api/analytics/univariate/{param_name} — per-parameter win-rate breakdown.
GET /api/analytics/summary                 — overall strategy analytics summary.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Annotated, Any, NamedTuple

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

import analytics.params  # noqa: F401 — triggers @register side-effects for all params

from analytics.candle_cache import CandleCache, _next_bar_close, _DEFAULT_INTERVAL, get_app_cache
from analytics.enrichment import enrich_batch, fetch_resolved
from analytics.registry import get_param_def, get_params_for_strategy
from analytics.schemas import SummaryResponse, UnivariateReportResponse
from analytics.stats.report import build_summary, build_univariate_report
from api.auth import get_current_user
from api.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ---------------------------------------------------------------------------
# Enriched-batch cache
# ---------------------------------------------------------------------------
# enrich_batch() is expensive (500 signals × all params). When a user clicks
# through several params on the same strategy, the underlying signals and
# candles don't change — only the report changes. Cache the enriched list
# per strategy and reuse it across param clicks until the next bar closes.

class _EnrichedEntry(NamedTuple):
    enriched: list[dict[str, Any]]
    expires_at: datetime


_enriched_cache: dict[str, _EnrichedEntry] = {}
_enriched_lock = threading.Lock()


def _get_enriched(
    strategy: str,
    db: Session,
    candle_cache: CandleCache,
) -> list[dict[str, Any]]:
    """Return enriched signals for a strategy, computing and caching on miss/expiry."""
    now = datetime.now(timezone.utc)

    with _enriched_lock:
        entry = _enriched_cache.get(strategy)
        if entry is not None and now < entry.expires_at:
            logger.debug("Enriched cache hit for strategy=%s", strategy)
            return entry.enriched

    logger.info("Enriched cache miss for strategy=%s — recomputing", strategy)
    signals = fetch_resolved(db, strategy=strategy)
    unique_pairs = sorted({(s.symbol, s.strategy) for s in signals})
    candle_cache.warm(unique_pairs)
    enriched = enrich_batch(signals, candle_cache=candle_cache)

    expires_at = _next_bar_close(_DEFAULT_INTERVAL, now)
    with _enriched_lock:
        _enriched_cache[strategy] = _EnrichedEntry(enriched=enriched, expires_at=expires_at)

    return enriched


@router.get(
    "/univariate/{param_name}",
    response_model=UnivariateReportResponse,
)
def get_univariate_report(
    param_name: Annotated[str, Path(description="Registered parameter name")],
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[CandleCache, Depends(get_app_cache)],
    strategy: str = Query(..., description="Strategy slug (required)"),
) -> UnivariateReportResponse:
    """Return per-bucket win-rate analysis for a single parameter."""
    param_def = get_param_def(param_name)
    if param_def is None:
        logger.warning("Unknown param requested: %s", param_name)
        raise HTTPException(
            status_code=404,
            detail=f"Parameter '{param_name}' is not registered",
        )
    enriched = _get_enriched(strategy, db, cache)
    report = build_univariate_report(
        param_name, param_def.dtype, strategy, enriched,
    )
    return UnivariateReportResponse(**report)


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    _cache: Annotated[CandleCache, Depends(get_app_cache)],
    strategy: str = Query(..., description="Strategy slug (required)"),
) -> SummaryResponse:
    """Return overall analytics summary for a strategy.

    Candle cache is intentionally not warmed here — warming 10+ symbols
    blocks for ~14 s on a cold cache, causing the landing page to time out.
    Non-candle params (session, spread tier, day of week, FVG geometry, etc.)
    are sufficient for the summary ranking.  Candle-dependent params are
    available in the per-param univariate endpoint where the user explicitly waits.
    """
    signals = fetch_resolved(db, strategy=strategy)
    enriched = enrich_batch(signals, candle_cache=None)
    param_defs = [
        {"name": p.name, "dtype": p.dtype}
        for p in get_params_for_strategy(strategy)
    ]
    result = build_summary(strategy, enriched, param_defs)
    return SummaryResponse(**result)
