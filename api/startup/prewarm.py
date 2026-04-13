"""
api/startup/prewarm.py
-----------------------
Background task that keeps the candle and enriched-signal caches warm.

Runs immediately at startup so the first analytics request hits a warm cache.
Repeats every _PREWARM_INTERVAL_SECONDS to stay ahead of the 15-min bar boundary.
"""
from __future__ import annotations

import asyncio
import logging

from analytics.candle_cache import STRATEGY_INTERVALS, get_app_cache
from analytics.enrichment import fetch_resolved
from analytics.routes_stats import prewarm_enriched_cache
from api.db import SessionLocal

logger = logging.getLogger(__name__)

_PREWARM_INTERVAL_SECONDS: int = 14 * 60  # slightly under 15 min to stay ahead of bar close
_PREWARM_SIGNAL_LIMIT: int = 2000


async def _warm_candles(loop: asyncio.AbstractEventLoop) -> None:
    """Warm the candle cache for all active (symbol, strategy) pairs."""
    db = SessionLocal()
    try:
        signals = fetch_resolved(db, limit=_PREWARM_SIGNAL_LIMIT)
        pairs = sorted({(s.symbol, s.strategy) for s in signals})
        if not pairs:
            return
        cache = get_app_cache()
        logger.info("Pre-warming candle cache for %d pair(s)", len(pairs))
        warmed, failed = await loop.run_in_executor(None, cache.warm, pairs)
        logger.info("Candle cache warm done — %d ok, %d failed", len(warmed), len(failed))
        if failed:
            logger.warning("Candle cache warm failed for: %s", failed)
    finally:
        db.close()


async def _warm_enriched(loop: asyncio.AbstractEventLoop) -> None:
    """Warm the enriched-signal cache for all known strategies."""
    known_strategies = list(STRATEGY_INTERVALS.keys())
    logger.info("Pre-warming enriched cache for strategies: %s", known_strategies)
    db = SessionLocal()
    try:
        cache = get_app_cache()
        await loop.run_in_executor(None, prewarm_enriched_cache, known_strategies, db, cache)
        logger.info("Enriched cache warm done")
    finally:
        db.close()


async def prewarm_loop() -> None:
    """Background task: warm the candle cache and enriched-signal cache on a timer.

    Two-phase warm per cycle:
      1. Candle cache  — fetches live OHLC from TradingView for every active pair.
      2. Enriched cache — runs all analytics params for each strategy.

    Failures are caught per-phase and logged without crashing the loop.
    """
    loop = asyncio.get_running_loop()
    while True:
        try:
            await _warm_candles(loop)
        except Exception:
            logger.exception("Error in candle cache pre-warm")
        try:
            await _warm_enriched(loop)
        except Exception:
            logger.exception("Error in enriched cache pre-warm")
        await asyncio.sleep(_PREWARM_INTERVAL_SECONDS)
