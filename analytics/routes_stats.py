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

from analytics.candle_cache import (
    CandleCache,
    get_app_cache,
    interval_for_strategy,
    next_bar_close,
)
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
# Per-strategy locks for double-checked locking: prevents two concurrent
# requests from both computing enrich_batch() for the same strategy when
# the shared cache is cold. The outer _enriched_lock only guards cache reads
# and per-strategy lock creation; the per-strategy lock serialises the
# expensive compute step.
_enriched_computing_locks: dict[str, threading.Lock] = {}


def _get_computing_lock(strategy: str) -> threading.Lock:
    """Return (creating if needed) the per-strategy computing lock."""
    with _enriched_lock:
        if strategy not in _enriched_computing_locks:
            _enriched_computing_locks[strategy] = threading.Lock()
        return _enriched_computing_locks[strategy]


def filter_by_symbol(
    enriched: list[dict[str, Any]],
    symbol: str | None,
) -> list[dict[str, Any]]:
    """Return enriched signals filtered to a single symbol, or all if symbol is None."""
    if symbol is None:
        return enriched
    return [r for r in enriched if r["symbol"] == symbol]


def prewarm_enriched_cache(
    strategies: list[str],
    db: Session,
    candle_cache: CandleCache,
) -> None:
    """Pre-warm the enriched signal cache for a list of strategy slugs.

    Intended to be called from the startup background task so the first
    analytics request hits a warm cache rather than blocking for several
    seconds. Skips strategies whose cache is still valid.
    """
    for strategy in strategies:
        get_enriched(strategy, db, candle_cache)


def get_enriched(
    strategy: str,
    db: Session,
    candle_cache: CandleCache,
) -> list[dict[str, Any]]:
    """Return enriched signals for a strategy, computing and caching on miss/expiry.

    Uses double-checked locking to prevent concurrent requests from both
    computing enrich_batch() for the same strategy on a cold cache:
    1. Fast path: check cache under the shared lock, return early on hit.
    2. Slow path: acquire the per-strategy computing lock (blocking), re-check
       the cache (it may have been filled while we waited), and only compute
       if still a miss.
    """
    now = datetime.now(timezone.utc)

    with _enriched_lock:
        entry = _enriched_cache.get(strategy)
        if entry is not None and now < entry.expires_at:
            logger.debug("Enriched cache hit for strategy=%s", strategy)
            return entry.enriched

    computing_lock = _get_computing_lock(strategy)
    with computing_lock:
        # Re-check after acquiring the per-strategy lock: a concurrent caller
        # may have computed and stored the result while we were waiting.
        with _enriched_lock:
            entry = _enriched_cache.get(strategy)
            if entry is not None and now < entry.expires_at:
                logger.debug("Enriched cache hit (post-lock re-check) for strategy=%s", strategy)
                return entry.enriched

        logger.info("Enriched cache miss for strategy=%s — recomputing", strategy)
        signals = fetch_resolved(db, strategy=strategy)
        _warmed, _failed = candle_cache.warm(list({(s.symbol, s.strategy) for s in signals}))
        if _failed:
            logger.warning(
                "Cache warm failed for %d pair(s) in strategy=%s: %s",
                len(_failed), strategy, _failed,
            )
        enriched = enrich_batch(signals, candle_cache=candle_cache)

        now = datetime.now(timezone.utc)
        expires_at = next_bar_close(interval_for_strategy(strategy), now)
        with _enriched_lock:
            _enriched_cache[strategy] = _EnrichedEntry(enriched=enriched, expires_at=expires_at)
            # Remove the per-strategy lock now that the result is cached.
            # The lock is only needed during the compute window; the next cache
            # miss will create a fresh one via _get_computing_lock's setdefault.
            _enriched_computing_locks.pop(strategy, None)

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
    symbol: str | None = Query(None, description="Filter by currency pair"),
) -> UnivariateReportResponse:
    """Return per-bucket win-rate analysis for a single parameter."""
    param_def = get_param_def(param_name)
    if param_def is None:
        logger.warning("Unknown param requested: %s", param_name)
        raise HTTPException(
            status_code=404,
            detail=f"Parameter '{param_name}' is not registered",
        )
    enriched = filter_by_symbol(get_enriched(strategy, db, cache), symbol)
    report = build_univariate_report(
        param_name, param_def.dtype, strategy, enriched,
    )
    return UnivariateReportResponse(**report)


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[CandleCache, Depends(get_app_cache)],
    strategy: str = Query(..., description="Strategy slug (required)"),
    symbol: str | None = Query(None, description="Filter by currency pair"),
) -> SummaryResponse:
    """Return overall analytics summary for a strategy.

    Uses the same get_enriched() cache as /univariate so both endpoints
    draw from an identical signal set. On a cold cache this may block while
    the prewarm task catches up, but in production the startup prewarm loop
    ensures the cache is warm before the first request lands.
    """
    enriched = filter_by_symbol(get_enriched(strategy, db, cache), symbol)
    all_params = get_params_for_strategy(strategy)
    param_defs = [{"name": p.name, "dtype": p.dtype} for p in all_params]
    result = build_summary(strategy, enriched, param_defs)
    return SummaryResponse(**result, partial=False, excluded_params=[])
