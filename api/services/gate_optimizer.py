"""
api/services/gate_optimizer.py
-------------------------------
Pure greedy forward-selection gate optimizer.

No DB access, no I/O. Takes enriched signals and confirmed params as plain
Python dicts and returns the selected conditions + performance stats.
"""
from __future__ import annotations

import logging
from typing import Any

from analytics.conditions import evaluate_all
from analytics.types import LOSS_RESOLUTION, WIN_RESOLUTION

logger = logging.getLogger(__name__)

MIN_RESOLVED = 5
DEFAULT_MIN_PASS_RATE = 0.40


def _win_rate(signals: list[dict[str, Any]], conditions: list[dict[str, Any]]) -> float | None:
    """Return win rate for signals that pass all conditions.

    Returns None when fewer than MIN_RESOLVED resolved signals pass.
    """
    wins = 0
    n = 0
    for sig in signals:
        params = sig.get("params", {})
        passed, _ = evaluate_all(conditions, params)
        if not passed:
            continue
        if sig.get("resolution") == WIN_RESOLUTION:
            wins += 1
            n += 1
        elif sig.get("resolution") == LOSS_RESOLUTION:
            n += 1
    return wins / n if n >= MIN_RESOLVED else None


def _pass_stats(
    signals: list[dict[str, Any]],
    conditions: list[dict[str, Any]],
) -> tuple[int, int]:
    """Return (pass_count, total_count) for the given condition set."""
    total = len(signals)
    passing = sum(
        1 for sig in signals
        if evaluate_all(conditions, sig.get("params", {}))[0]
    )
    return passing, total


def _make_condition(param_name: str, delta: float, best_bucket: str) -> dict[str, Any]:
    """Build a single gate condition dict from a confirmed param row."""
    op = "ne" if delta < 0 else "eq"
    return {"param": param_name, "op": op, "value": best_bucket}


def optimize_gates(
    enriched: list[dict[str, Any]],
    confirmed_params: list[dict[str, Any]],
    min_pass_rate: float = DEFAULT_MIN_PASS_RATE,
) -> dict[str, Any]:
    """Run greedy forward selection over confirmed params.

    Parameters
    ----------
    enriched :
        Enriched signal list from ``enrich_batch()``. Each dict must have
        a ``"params"`` key and a ``"resolution"`` field.
    confirmed_params :
        FDR-confirmed param rows from ``build_summary()``.
        Each must have ``param_name``, ``delta``, ``best_bucket``.
    min_pass_rate :
        Minimum fraction of all signals that must pass the gate.

    Returns
    -------
    dict with keys: conditions_selected, win_rate_baseline, win_rate_optimized,
    delta, pass_rate, pass_count, total_signals, confirmed_params_found, reason.
    """
    total = len(enriched)
    baseline_wr = _win_rate(enriched, [])

    if baseline_wr is None:
        return _empty_result(confirmed_params, total, "insufficient_resolved_signals")

    ranked = sorted(confirmed_params, key=lambda r: abs(r.get("delta") or 0.0), reverse=True)
    selected: list[dict[str, Any]] = []
    current_wr = baseline_wr

    for row in ranked:
        param_name = row.get("param_name", "")
        delta = row.get("delta") or 0.0
        best_bucket = row.get("best_bucket", "")
        if not param_name or not best_bucket:
            continue

        candidate = _make_condition(param_name, delta, best_bucket)
        trial = selected + [candidate]

        trial_wr = _win_rate(enriched, trial)
        if trial_wr is None:
            continue

        pass_count, _ = _pass_stats(enriched, trial)
        pass_rate = pass_count / total if total > 0 else 0.0

        if trial_wr > current_wr and pass_rate >= min_pass_rate:
            selected = trial
            current_wr = trial_wr
            logger.debug("Added gate condition: %s (wr %.3f → %.3f)", param_name, current_wr, trial_wr)

    pass_count, _ = _pass_stats(enriched, selected)
    pass_rate = pass_count / total if total > 0 else 0.0
    optimized_wr = _win_rate(enriched, selected) or baseline_wr

    return {
        "conditions_selected": selected,
        "win_rate_baseline": baseline_wr,
        "win_rate_optimized": optimized_wr,
        "delta": round(optimized_wr - baseline_wr, 4),
        "pass_rate": round(pass_rate, 4),
        "pass_count": pass_count,
        "total_signals": total,
        "confirmed_params_found": len(confirmed_params),
        "reason": None,
    }


def _empty_result(
    confirmed_params: list[dict[str, Any]],
    total: int,
    reason: str,
) -> dict[str, Any]:
    """Return a zeroed-out result with a reason string."""
    return {
        "conditions_selected": [],
        "win_rate_baseline": None,
        "win_rate_optimized": None,
        "delta": None,
        "pass_rate": None,
        "pass_count": 0,
        "total_signals": total,
        "confirmed_params_found": len(confirmed_params),
        "reason": reason,
    }
