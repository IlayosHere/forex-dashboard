"""
analytics/confirmed_cache.py
-----------------------------
In-process TTL cache of per-strategy confirmed parameters.

Confirmed params are derived from FDR-filtered build_summary() output.
Computing that is expensive (full enrichment pass), so we cache the result
for 30 minutes — confirmed params change slowly relative to live signal flow.

Used by runner/grade_runner.py to compute A/B/C/D grades at signal fire-time
without re-running the full summary on every scan cycle.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from analytics.registry import get_params_for_strategy
from analytics.stats.report import build_summary

logger = logging.getLogger(__name__)

_TTL_SECONDS = 60 * 30  # 30 minutes

_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def get_confirmed_params(
    enriched: list[dict[str, Any]],
    strategy: str,
) -> list[dict[str, Any]]:
    """Return cached confirmed params, refreshing on TTL expiry.

    Parameters
    ----------
    enriched :
        Pre-computed enriched signal list for this strategy. Only used on a
        cache miss — on a hit the cached value is returned immediately.
    strategy :
        Strategy slug used as the cache key.

    Returns
    -------
    List of param dicts with ``fdr_status="confirmed"``, each containing
    at minimum ``param_name``, ``delta``, and ``best_bucket``.
    """
    now = time.monotonic()
    cached = _cache.get(strategy)
    if cached is not None and (now - cached[0]) < _TTL_SECONDS:
        return cached[1]

    confirmed = _compute_confirmed(enriched, strategy)
    _cache[strategy] = (now, confirmed)
    logger.info(
        "Confirmed params cache refreshed for strategy=%s: %d confirmed",
        strategy, len(confirmed),
    )
    return confirmed


def invalidate(strategy: str | None = None) -> None:
    """Drop cached confirmed params — call after threshold or model changes.

    Pass strategy=None to clear the entire cache.
    """
    if strategy is None:
        _cache.clear()
    else:
        _cache.pop(strategy, None)


def _compute_confirmed(
    enriched: list[dict[str, Any]],
    strategy: str,
) -> list[dict[str, Any]]:
    """Run build_summary and extract FDR-confirmed rows."""
    if not enriched:
        return []
    param_defs = [
        {"name": p.name, "dtype": p.dtype}
        for p in get_params_for_strategy(strategy)
    ]
    summary = build_summary(strategy, enriched, param_defs)
    return [
        row for row in summary.get("top_correlations", [])
        if row.get("fdr_status") == "confirmed"
    ]
