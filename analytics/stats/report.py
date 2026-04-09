"""
analytics/stats/report.py
-------------------------
Assemble univariate statistical reports from enriched signals.
"""
from __future__ import annotations

import logging
from typing import Any

from analytics.stats.filters import (
    category_split,
    filter_min_bucket,
    quintile_split,
)
from analytics.stats.univariate import (
    chi_squared_test,
    point_biserial_test,
    win_rate_by_bucket,
)
from analytics.types import LOSS_RESOLUTION, WIN_RESOLUTION

logger = logging.getLogger(__name__)

CATEGORICAL_DTYPES = frozenset({"str", "bool"})
NUMERIC_DTYPES = frozenset({"float", "int"})
SIGNIFICANCE_THRESHOLD = 0.05


def build_univariate_report(
    param_name: str,
    dtype: str,
    strategy: str,
    enriched: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a full univariate analysis report for one parameter.

    Parameters
    ----------
    param_name : str
        Parameter key inside each signal's ``params`` dict.
    dtype : str
        One of "float", "int", "str", "bool".
    strategy : str
        Strategy slug for labelling.
    enriched : list[dict]
        Enriched signal dicts with ``params`` and ``resolution``.

    Returns
    -------
    dict with buckets, win rates, and significance test results.
    """
    total_signals = len(enriched)

    buckets = _split_by_dtype(enriched, param_name, dtype)
    buckets = filter_min_bucket(buckets)

    bucket_stats = win_rate_by_bucket(buckets)

    chi2, chi_p = _safe_chi_squared(buckets)
    corr, corr_p = _safe_point_biserial(enriched, param_name, dtype)

    return {
        "param_name": param_name,
        "dtype": "categorical" if dtype in CATEGORICAL_DTYPES else "numeric",
        "strategy": strategy,
        "total_signals": total_signals,
        "buckets": [b.as_dict() for b in bucket_stats],
        "chi_squared": chi2,
        "chi_p_value": chi_p,
        "correlation": corr,
        "correlation_p_value": corr_p,
    }


def build_summary(
    strategy: str,
    enriched: list[dict[str, Any]],
    param_defs: list[dict[str, str]],
) -> dict[str, Any]:
    """Build a summary ranking all params by statistical significance.

    Parameters
    ----------
    strategy : str
        Strategy slug.
    enriched : list[dict]
        Enriched signal dicts.
    param_defs : list[dict]
        Each entry has ``"name"`` and ``"dtype"`` keys.

    Returns
    -------
    dict with overall stats and ranked parameter correlations.
    """
    wins = sum(1 for s in enriched if s.get("resolution") == WIN_RESOLUTION)
    total = sum(
        1 for s in enriched
        if s.get("resolution") in (WIN_RESOLUTION, LOSS_RESOLUTION)
    )
    overall_wr = wins / total if total > 0 else 0.0

    correlations = _rank_params(enriched, param_defs)

    return {
        "strategy": strategy,
        "total_resolved": total,
        "win_rate_overall": overall_wr,
        "params_analyzed": len(param_defs),
        "top_correlations": correlations,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _split_by_dtype(
    enriched: list[dict[str, Any]],
    param_name: str,
    dtype: str,
) -> dict[str, list[dict[str, Any]]]:
    """Choose split method based on dtype."""
    if dtype in CATEGORICAL_DTYPES:
        return category_split(enriched, param_name)
    return quintile_split(enriched, param_name)


def _safe_chi_squared(
    buckets: dict[str, list[dict[str, Any]]],
) -> tuple[float | None, float | None]:
    """Run chi-squared test, returning (None, None) on failure."""
    result = chi_squared_test(buckets)
    if result is None:
        return (None, None)
    return result


def _safe_point_biserial(
    enriched: list[dict[str, Any]],
    param_name: str,
    dtype: str,
) -> tuple[float | None, float | None]:
    """Run point-biserial only for numeric params."""
    if dtype not in NUMERIC_DTYPES:
        return (None, None)
    result = point_biserial_test(enriched, param_name)
    if result is None:
        return (None, None)
    return result


def _rank_params(
    enriched: list[dict[str, Any]],
    param_defs: list[dict[str, str]],
) -> list[dict[str, Any]]:
    """Compute significance for each param and rank by p-value."""
    rows: list[dict[str, Any]] = []
    for pdef in param_defs:
        name = pdef["name"]
        dtype = pdef["dtype"]
        row = _compute_param_significance(enriched, name, dtype)
        if row is not None:
            rows.append(row)
    rows.sort(key=lambda r: r["p_value"])
    return rows


def _compute_param_significance(
    enriched: list[dict[str, Any]],
    name: str,
    dtype: str,
) -> dict[str, Any] | None:
    """Get correlation/p-value for a single param."""
    if dtype in NUMERIC_DTYPES:
        result = point_biserial_test(enriched, name)
        if result is None:
            return None
        corr, p_val = result
    else:
        buckets = category_split(enriched, name)
        buckets = filter_min_bucket(buckets)
        result = chi_squared_test(buckets)
        if result is None:
            return None
        corr, p_val = result

    return {
        "param_name": name,
        "correlation": corr,
        "p_value": p_val,
        "significant": p_val < SIGNIFICANCE_THRESHOLD,
    }
