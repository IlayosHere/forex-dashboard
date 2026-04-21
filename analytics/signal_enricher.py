"""
analytics/signal_enricher.py
-----------------------------
Compute and persist analytics params at signal-fire time.

Called by the runner immediately after a signal passes dedup, so candles are
fresh and ``_find_signal_bar`` can always locate the signal's bar. Results are
stored in ``signal_metadata["_analytics_params"]`` and re-used by
``enrich_batch`` instead of recomputing against the stale live cache.
"""
from __future__ import annotations

import logging
from typing import Any

import analytics.params  # noqa: F401 — triggers @register side-effects

from analytics.candle_cache import CandleCache
from analytics.registry import resolve_all_params
from shared.signal import Signal

logger = logging.getLogger(__name__)

ANALYTICS_PARAMS_KEY = "_analytics_params"


def compute_and_attach(signal: Signal, candle_cache: CandleCache) -> None:
    """Compute all analytics params for *signal* and store them in its metadata.

    Warms the candle cache for (symbol, strategy) if not already warm, then
    runs ``resolve_all_params``. Results are written to
    ``signal.metadata[ANALYTICS_PARAMS_KEY]``. Any pre-existing value under
    that key is overwritten.

    Errors from individual params are caught inside ``resolve_all_params`` and
    recorded as ``None`` — this function never raises.
    """
    pair = (signal.symbol, signal.strategy)
    if candle_cache.get(signal.symbol, signal.strategy) is None:
        warmed, failed = candle_cache.warm([pair])
        if failed:
            logger.warning(
                "Candle fetch failed for %s/%s — analytics params will be partial",
                signal.symbol, signal.strategy,
            )

    candles = candle_cache.get(signal.symbol, signal.strategy)
    params: dict[str, Any] = resolve_all_params(signal, signal.strategy, candles=candles)
    signal.metadata[ANALYTICS_PARAMS_KEY] = params
    logger.debug(
        "Analytics params computed for %s %s: %d params, %d non-null",
        signal.symbol, signal.strategy,
        len(params),
        sum(1 for v in params.values() if v is not None),
    )
