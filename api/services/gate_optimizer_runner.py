"""
api/services/gate_optimizer_runner.py
---------------------------------------
DB-aware runner that wires fetch_resolved + enrich_batch + build_summary
into the pure gate_optimizer.

Keeps all I/O out of gate_optimizer.py so the core logic stays testable.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from analytics.candle_cache import CandleCache
from analytics.confirmed_cache import get_confirmed_params
from analytics.enrichment import enrich_batch, fetch_resolved
from analytics.registry import get_params_for_strategy
from analytics.stats.report import build_summary
from api.services.gate_optimizer import optimize_gates

logger = logging.getLogger(__name__)


def run_optimizer(
    db: Session,
    strategy: str,
    cache: CandleCache,
    min_pass_rate: float,
) -> dict[str, Any]:
    """Fetch, enrich, analyse, and optimise gates for one strategy.

    Parameters
    ----------
    db :
        Active SQLAlchemy session.
    strategy :
        Strategy slug.
    cache :
        App-scoped CandleCache (injected from FastAPI dependency).
    min_pass_rate :
        Minimum signal pass-through fraction required to keep a condition.

    Returns
    -------
    Result dict from ``optimize_gates()`` plus a ``"strategy"`` key.
    """
    signals = fetch_resolved(db, strategy=strategy)
    if not signals:
        logger.warning("run_optimizer: no resolved signals for strategy=%s", strategy)
        return _no_data_result(strategy)

    cache.warm(list({(s.symbol, s.strategy) for s in signals}))
    enriched = enrich_batch(signals, candle_cache=cache)

    param_defs = [
        {"name": p.name, "dtype": p.dtype}
        for p in get_params_for_strategy(strategy)
    ]
    summary = build_summary(strategy, enriched, param_defs)
    confirmed = [
        row for row in summary.get("top_correlations", [])
        if row.get("fdr_status") == "confirmed"
    ]

    result = optimize_gates(enriched, confirmed, min_pass_rate=min_pass_rate)
    result["strategy"] = strategy

    get_confirmed_params(enriched, strategy)

    logger.info(
        "Gate optimizer finished for strategy=%s: %d conditions selected, wr %.3f → %.3f",
        strategy,
        len(result["conditions_selected"]),
        result.get("win_rate_baseline") or 0.0,
        result.get("win_rate_optimized") or 0.0,
    )
    return result


def _no_data_result(strategy: str) -> dict[str, Any]:
    """Return a zeroed result when no resolved signals are available."""
    return {
        "strategy": strategy,
        "conditions_selected": [],
        "win_rate_baseline": None,
        "win_rate_optimized": None,
        "delta": None,
        "pass_rate": None,
        "pass_count": 0,
        "total_signals": 0,
        "confirmed_params_found": 0,
        "reason": "no_resolved_signals",
    }
