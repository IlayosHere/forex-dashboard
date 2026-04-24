"""
analytics/scoring.py
--------------------
Rule-based composite setup quality score.

Score = sum of (weight_i * indicator_i) for confirmed params only.
- weight_i = effect size in percentage points (clipped to [2, 20])
- indicator_i = +1 if signal falls in the "prefer" bucket,
                -1 if in the "avoid" bucket,
                 0 otherwise
Output: integer approximately in range [-100, +100].
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from analytics.registry import get_param_def, resolve_all_params

logger = logging.getLogger(__name__)

_WEIGHT_MIN = 2
_WEIGHT_MAX = 20


def compute_score(
    signal: Any,
    strategy: str,
    candles: pd.DataFrame | None,
    confirmed_params: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute composite quality score from FDR-confirmed parameters.

    Parameters
    ----------
    signal : Any
        SignalModel instance (or any object with signal fields).
    strategy : str
        Strategy slug.
    candles : pd.DataFrame | None
        OHLC candle history for this signal's symbol; None if unavailable.
    confirmed_params : list[dict]
        Rows from build_summary top_correlations where fdr_status="confirmed".
        Each row must have: param_name, delta, best_bucket.

    Returns
    -------
    dict with keys: score, max_possible, contributing, explanation.
    """
    if not confirmed_params:
        return _empty_result()

    param_values = _compute_param_values(signal, strategy, candles, confirmed_params)
    contributing, score, max_possible = _score_params(confirmed_params, param_values)
    explanation = _build_explanation(contributing)

    return {
        "score": score,
        "max_possible": max_possible,
        "contributing": contributing,
        "explanation": explanation,
    }


def _empty_result() -> dict[str, Any]:
    """Return a zero-score result when no confirmed params exist."""
    return {
        "score": 0,
        "max_possible": 0,
        "contributing": [],
        "explanation": "0 edge(s) matched, 0 violated, 0 neutral",
    }


def _compute_param_values(
    signal: Any,
    strategy: str,
    candles: pd.DataFrame | None,
    confirmed_params: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute current values for all confirmed params."""
    needed_names = {p["param_name"] for p in confirmed_params}
    all_values = resolve_all_params(signal, strategy, candles=candles)
    return {k: v for k, v in all_values.items() if k in needed_names}


def _score_params(
    confirmed_params: list[dict[str, Any]],
    param_values: dict[str, Any],
) -> tuple[list[dict[str, Any]], int, int]:
    """Build contributing list and compute score + max_possible."""
    contributing: list[dict[str, Any]] = []
    score = 0
    max_possible = 0

    for param in confirmed_params:
        name = param.get("param_name")
        delta = param.get("delta")
        best_bucket = param.get("best_bucket")

        if name is None or delta is None or best_bucket is None:
            continue

        weight = int(min(_WEIGHT_MAX, max(_WEIGHT_MIN, round(abs(delta) * 100))))
        max_possible += weight

        current_value = param_values.get(name)
        indicator = _compute_indicator(current_value, best_bucket, delta)
        score += weight * indicator

        contributing.append({
            "param_name": name,
            "bucket": str(current_value) if current_value is not None else None,
            "indicator": indicator,
            "weight": weight,
        })

    return contributing, score, max_possible


def _compute_indicator(
    current_value: Any,
    best_bucket: str,
    delta: float,
) -> int:
    """Return +1, -1, or 0 depending on whether the current value matches best_bucket."""
    if current_value is None:
        return 0
    value_str = str(current_value)
    if value_str != str(best_bucket):
        return 0
    return 1 if delta > 0 else -1


def _build_explanation(contributing: list[dict[str, Any]]) -> str:
    """Summarise matched / violated / neutral counts as a human-readable string."""
    pos = sum(1 for c in contributing if c["indicator"] == 1)
    neg = sum(1 for c in contributing if c["indicator"] == -1)
    neutral = sum(1 for c in contributing if c["indicator"] == 0)
    return f"{pos} edge(s) matched, {neg} violated, {neutral} neutral"
