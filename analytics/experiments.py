"""
analytics/experiments.py
------------------------
Pure historical backtest evaluator for saved experiments.

Applies a set of AND-combined parameter conditions to all historical signals
for a strategy and computes win-rate statistics vs baseline. Used by both the
ephemeral /evaluate endpoint and the saved-experiment /run endpoint.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.conditions import evaluate_all
from analytics.signal_enricher import ANALYTICS_PARAMS_KEY
from analytics.stats.univariate import two_proportion_ci
from analytics.types import LOSS_RESOLUTION, WIN_RESOLUTION
from api.models import SignalModel

logger = logging.getLogger(__name__)


def evaluate_experiment(
    db: Session,
    strategy: str,
    conditions: list[dict[str, Any]],
    date_from: datetime | None,
    date_to: datetime | None,
) -> dict[str, Any]:
    """Evaluate conditions against historical signals for a strategy.

    Returns a dict matching ExperimentResultResponse fields.
    """
    signals = _fetch_signals(db, strategy, date_from, date_to)
    referenced_params = sorted({c["param"] for c in conditions})

    total = len(signals)
    resolved = [s for s in signals if s.resolution in (WIN_RESOLUTION, LOSS_RESOLUTION)]
    baseline_wr = _win_rate(resolved)

    passing: list[SignalModel] = []
    failure_counts = [0] * len(conditions)

    for sig in signals:
        params = (sig.signal_metadata or {}).get(ANALYTICS_PARAMS_KEY, {})
        passed, failed = evaluate_all(conditions, params)
        for idx in failed:
            failure_counts[idx] += 1
        if passed:
            passing.append(sig)

    resolved_passing = [s for s in passing if s.resolution in (WIN_RESOLUTION, LOSS_RESOLUTION)]
    wr_passed = _win_rate(resolved_passing)
    delta = (wr_passed - baseline_wr) if wr_passed is not None else None

    return {
        "strategy": strategy,
        "date_from": date_from,
        "date_to": date_to,
        "total_signals": total,
        "resolved_signals": len(resolved),
        "passing_signals": len(passing),
        "resolved_passing": len(resolved_passing),
        "win_rate_passed": wr_passed,
        "win_rate_baseline": baseline_wr,
        "delta_vs_baseline": delta,
        "per_condition_failure_count": failure_counts,
        "per_param_breakdown": _per_param_breakdown(resolved_passing, referenced_params),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_signals(
    db: Session,
    strategy: str,
    date_from: datetime | None,
    date_to: datetime | None,
) -> list[SignalModel]:
    """Return all signals for a strategy within the date range."""
    q = select(SignalModel).where(SignalModel.strategy == strategy)
    if date_from is not None:
        q = q.where(SignalModel.candle_time >= date_from)
    if date_to is not None:
        q = q.where(SignalModel.candle_time <= date_to)
    return list(db.scalars(q).all())


def _win_rate(signals: list[SignalModel]) -> float | None:
    """Return win rate for resolved signals, or None if count is 0."""
    if not signals:
        return None
    wins = sum(1 for s in signals if s.resolution == WIN_RESOLUTION)
    return wins / len(signals)


def _per_param_breakdown(
    resolved: list[SignalModel],
    param_names: list[str],
) -> list[dict[str, Any]]:
    """Build per-bucket win-rate stats for each param referenced in conditions."""
    breakdowns = []
    for name in param_names:
        buckets = _bucket_signals(resolved, name)
        stats = _compute_bucket_stats(buckets)
        if stats:
            breakdowns.append({"param_name": name, "buckets": stats})
    return breakdowns


def _bucket_signals(
    signals: list[SignalModel],
    param_name: str,
) -> dict[str, list[SignalModel]]:
    """Group signals by their value for param_name."""
    buckets: dict[str, list[SignalModel]] = {}
    for sig in signals:
        val = (sig.signal_metadata or {}).get(ANALYTICS_PARAMS_KEY, {}).get(param_name)
        key = str(val) if val is not None else "(null)"
        buckets.setdefault(key, []).append(sig)
    return buckets


def _compute_bucket_stats(
    buckets: dict[str, list[SignalModel]],
) -> list[dict[str, Any]]:
    """Compute win rate + Wilson CI for each bucket."""
    total_wins = sum(
        sum(1 for s in sigs if s.resolution == WIN_RESOLUTION)
        for sigs in buckets.values()
    )
    total_n = sum(len(sigs) for sigs in buckets.values())

    stats = []
    for bucket, sigs in buckets.items():
        wins = sum(1 for s in sigs if s.resolution == WIN_RESOLUTION)
        n = len(sigs)
        wr = wins / n if n > 0 else 0.0
        ci = two_proportion_ci(wins, n, total_wins - wins, total_n - n, z=1.96)
        ci_lo = ci[1] if ci else 0.0
        ci_hi = ci[2] if ci else 0.0
        stats.append({
            "bucket": bucket,
            "n": n,
            "wins": wins,
            "win_rate": wr,
            "ci_lo": ci_lo,
            "ci_hi": ci_hi,
        })
    return sorted(stats, key=lambda x: x["win_rate"], reverse=True)
