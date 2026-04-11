"""
analytics/enrichment.py
-----------------------
Fetch resolved signals and enrich them with derived parameters.

Three entry points:
  - fetch_resolved()      — query DB for TP_HIT / SL_HIT signals
  - enrich_batch()        — attach computed params to each signal
  - enrich_with_candles() — convenience wrapper that auto-creates a CandleCache
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.candle_cache import (
    CandleCache,
    cached_atr,
    cached_d1,
    cached_ema20_h1,
    cached_h1,
)
from analytics.registry import resolve_all_params
from api.models import SignalModel

logger = logging.getLogger(__name__)

_MAX_LIMIT = 2000
_DEFAULT_LIMIT = 500

_SIGNAL_FIELDS: list[str] = [
    "id", "strategy", "symbol", "direction", "candle_time",
    "entry", "sl", "tp", "lot_size", "risk_pips", "spread_pips",
    "signal_metadata", "created_at", "resolution", "resolved_at",
    "resolved_price", "resolution_candles",
]


def fetch_resolved(
    db: Session,
    strategy: str | None = None,
    symbol: str | None = None,
    limit: int = _DEFAULT_LIMIT,
) -> list[SignalModel]:
    """Query resolved signals (TP_HIT or SL_HIT) with optional filters.

    Parameters
    ----------
    db : Session
        SQLAlchemy session.
    strategy : str | None
        Optional strategy slug filter.
    symbol : str | None
        Optional currency pair filter.
    limit : int
        Max rows to return (default 500, max 2000).
    """
    clamped = min(max(limit, 1), _MAX_LIMIT)
    stmt = select(SignalModel).where(
        SignalModel.resolution.in_(["TP_HIT", "SL_HIT"]),
    )
    if strategy is not None:
        stmt = stmt.where(SignalModel.strategy == strategy)
    if symbol is not None:
        stmt = stmt.where(SignalModel.symbol == symbol)
    stmt = stmt.order_by(SignalModel.candle_time.desc()).limit(clamped)
    return list(db.scalars(stmt).all())


def _signal_to_dict(signal: SignalModel) -> dict[str, Any]:
    """Extract core signal fields into a plain dict."""
    return {field: getattr(signal, field) for field in _SIGNAL_FIELDS}


def enrich_batch(
    signals: list[SignalModel],
    candle_cache: CandleCache | None = None,
) -> list[dict[str, Any]]:
    """Enrich a list of signals with all applicable derived params.

    Parameters
    ----------
    signals : list[SignalModel]
        Resolved signals from the database.
    candle_cache : CandleCache | None
        Optional candle cache for params that need OHLC history.
    """
    # Pre-compute and hold strong references to all derived series before the
    # signal loop.  The module-level WeakValueDictionary memos evict entries
    # the moment refcount drops to zero — which happens at the end of each
    # param function call when the local variable goes out of scope.  By
    # storing the results here, we keep refcount > 0 for the entire batch so
    # the memos remain valid for every subsequent lookup.
    _derived_hold: dict[tuple[str, str], tuple] = {}
    if candle_cache is not None:
        unique_pairs = {(s.symbol, s.strategy) for s in signals}
        for symbol, strategy in unique_pairs:
            df = candle_cache.get(symbol, strategy)
            if df is not None:
                h1 = cached_h1(df)
                _derived_hold[(symbol, strategy)] = (
                    df,
                    h1,
                    cached_atr(df),
                    cached_atr(h1),      # h1_trend_strength_bucket uses cached_atr(h1)
                    cached_d1(df),
                    cached_ema20_h1(h1),
                )

    results: list[dict[str, Any]] = []
    for signal in signals:
        row = _signal_to_dict(signal)
        candles = None
        if candle_cache is not None:
            candles = candle_cache.get(signal.symbol, signal.strategy)
        params = resolve_all_params(signal, signal.strategy, candles=candles)
        row["params"] = params
        results.append(row)
    return results


def enrich_with_candles(
    signals: list[SignalModel],
) -> list[dict[str, Any]]:
    """Enrich signals with a fresh per-call ``CandleCache``. Not for routes.

    This convenience helper is for scripts and tests that run outside a
    FastAPI request scope. Production routes should inject the app-scoped
    cache via ``Depends(get_app_cache)`` and call ``enrich_batch`` directly.

    Pre-warms the cache per ``(symbol, strategy)`` pair so each strategy's
    fetches hit its registered timeframe. Logs a single line per call with
    the count of warmed vs. failed pairs.

    Fetch failures degrade gracefully: ``CandleCache.get()`` returns ``None``
    for that ``(symbol, strategy)`` and ``resolve_all_params`` skips every
    candle-dependent param for those signals — the response still ships.
    """
    cache = CandleCache()
    unique_pairs = sorted({(s.symbol, s.strategy) for s in signals})
    warmed, failed = cache.warm(unique_pairs)
    logger.info(
        "CandleCache warmed: %d ok, %d failed (of %d unique pairs)",
        len(warmed), len(failed), len(unique_pairs),
    )
    if failed:
        logger.warning(
            "CandleCache failed pairs: %s",
            ", ".join(f"{sym}/{strat}" for sym, strat in failed),
        )
    return enrich_batch(signals, candle_cache=cache)
