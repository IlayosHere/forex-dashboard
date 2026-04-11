"""
analytics/stats/report.py
-------------------------
Assemble univariate statistical reports from enriched signals.
"""
from __future__ import annotations

from typing import Any

from analytics.stats.classification import (
    CI_LEVELS,
    ECONOMIC_THRESHOLD,
    Z_CRITICAL,
    best_bucket_analysis,
)
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

CATEGORICAL_DTYPES = frozenset({"str", "bool"})
NUMERIC_DTYPES = frozenset({"float", "int"})
# p-value alpha for the legacy `significant` boolean. Unrelated to
# ECONOMIC_THRESHOLD (an effect-size cutoff in win-rate fraction).
SIGNIFICANCE_THRESHOLD = 0.05

__all__ = [
    "CI_LEVELS",
    "ECONOMIC_THRESHOLD",
    "Z_CRITICAL",
    "build_summary",
    "build_univariate_report",
]

_EMPTY_CI_FIELDS: dict[str, Any] = {
    "delta": None,
    "ci_lo": None,
    "ci_hi": None,
    "best_bucket": None,
    "level": None,
}


def build_univariate_report(
    param_name: str,
    dtype: str,
    strategy: str,
    enriched: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a full univariate report for one parameter.

    Returns a dict with buckets, win rates, legacy chi2/point-biserial
    p-values, and the CI-based classification fields
    ``delta``, ``ci_lo``, ``ci_hi``, ``best_bucket``, ``level``.
    """
    total_signals = len(enriched)

    raw_buckets = _split_by_dtype(enriched, param_name, dtype)
    filtered = filter_min_bucket(raw_buckets)

    bucket_stats = win_rate_by_bucket(filtered)

    chi2, chi_p = _safe_chi_squared(filtered)
    corr, corr_p = _safe_point_biserial(enriched, param_name, dtype)
    ci_fields = best_bucket_analysis(filtered) or _EMPTY_CI_FIELDS

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
        **ci_fields,
    }


def build_summary(
    strategy: str,
    enriched: list[dict[str, Any]],
    param_defs: list[dict[str, str]],
) -> dict[str, Any]:
    """Build a summary with overall stats + params ranked by CI conclusiveness."""
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
    """Rank params by CI conclusiveness; nulls/'none' sort to bottom."""
    rows: list[dict[str, Any]] = []
    for pdef in param_defs:
        row = _compute_param_significance(enriched, pdef["name"], pdef["dtype"])
        if row is not None:
            rows.append(row)
    rows.sort(key=_rank_sort_key)
    return rows


def _rank_sort_key(row: dict[str, Any]) -> tuple[int, float]:
    """Sort key: (group, -strength). group=0 for populated rows, 1 for
    null-level rows; within group, lower -strength sorts first (descending
    by strength)."""
    delta = row.get("delta")
    level = row.get("level")
    if delta is None or level is None:
        return (1, 0.0)
    ci_lo = row.get("ci_lo")
    ci_hi = row.get("ci_hi")
    if ci_lo is not None and ci_hi is not None and not (ci_lo < 0 < ci_hi):
        strength = max(abs(ci_lo), abs(ci_hi))
    else:
        strength = abs(delta)
    return (0, -strength)


def _compute_param_significance(
    enriched: list[dict[str, Any]],
    name: str,
    dtype: str,
) -> dict[str, Any]:
    """Compute CI analysis + legacy p-value for a single param."""
    raw_buckets = _split_by_dtype(enriched, name, dtype)
    filtered = filter_min_bucket(raw_buckets)

    corr, p_val = _legacy_significance(enriched, filtered, name, dtype)
    ci_fields = best_bucket_analysis(filtered) or _EMPTY_CI_FIELDS

    return {
        "param_name": name,
        "correlation": corr,
        "p_value": p_val,
        "significant": p_val is not None and p_val < SIGNIFICANCE_THRESHOLD,
        **ci_fields,
    }


def _legacy_significance(
    enriched: list[dict[str, Any]],
    filtered: dict[str, list[dict[str, Any]]],
    name: str,
    dtype: str,
) -> tuple[float | None, float | None]:
    """Dispatch to the dtype-appropriate legacy test (chi2 or point-biserial)."""
    if dtype in NUMERIC_DTYPES:
        return _safe_point_biserial(enriched, name, dtype)
    return _safe_chi_squared(filtered)
