"""
tests/test_analytics_stats.py
------------------------------
Unit tests for analytics/stats/ — filters, univariate, and report.
Uses synthetic enriched signal dicts with known distributions.
"""
from __future__ import annotations

from typing import Any

import pytest

from analytics.stats.filters import category_split, filter_min_bucket, quintile_split
from analytics.stats.report import build_summary, build_univariate_report
from analytics.stats.univariate import (
    _wilson_ci,
    chi_squared_test,
    point_biserial_test,
    win_rate_by_bucket,
)


def _enriched(
    resolution: str = "TP_HIT",
    **params: Any,
) -> dict[str, Any]:
    """Build a minimal enriched signal dict."""
    return {"resolution": resolution, "params": params}


def _batch(
    n_wins: int,
    n_losses: int,
    **param_values: Any,
) -> list[dict[str, Any]]:
    """Build a batch of enriched signals with fixed param values."""
    signals: list[dict[str, Any]] = []
    for _ in range(n_wins):
        signals.append(_enriched("TP_HIT", **param_values))
    for _ in range(n_losses):
        signals.append(_enriched("SL_HIT", **param_values))
    return signals


# ---------------------------------------------------------------------------
# filters.py
# ---------------------------------------------------------------------------


def test_category_split_groups_correctly() -> None:
    signals = [
        _enriched("TP_HIT", session="LONDON"),
        _enriched("SL_HIT", session="LONDON"),
        _enriched("TP_HIT", session="ASIAN"),
    ]
    buckets = category_split(signals, "session")
    assert set(buckets.keys()) == {"LONDON", "ASIAN"}
    assert len(buckets["LONDON"]) == 2
    assert len(buckets["ASIAN"]) == 1


def test_category_split_skips_none() -> None:
    signals = [
        _enriched("TP_HIT", session="LONDON"),
        _enriched("TP_HIT", session=None),
    ]
    buckets = category_split(signals, "session")
    assert "LONDON" in buckets
    assert len(buckets) == 1


def test_quintile_split_creates_buckets() -> None:
    signals = [_enriched("TP_HIT", ratio=float(i)) for i in range(100)]
    buckets = quintile_split(signals, "ratio", n_buckets=5)
    assert len(buckets) == 5
    total = sum(len(v) for v in buckets.values())
    assert total == 100


def test_quintile_split_empty() -> None:
    assert quintile_split([], "ratio") == {}


def test_filter_min_bucket_removes_small() -> None:
    buckets = {
        "A": list(range(50)),
        "B": list(range(10)),
        "C": list(range(35)),
    }
    filtered = filter_min_bucket(buckets, min_size=30)
    assert "A" in filtered
    assert "C" in filtered
    assert "B" not in filtered


# ---------------------------------------------------------------------------
# univariate.py
# ---------------------------------------------------------------------------


def test_wilson_ci_known_values() -> None:
    lo, hi = _wilson_ci(50, 100)
    assert lo == pytest.approx(0.4, abs=0.05)
    assert hi == pytest.approx(0.6, abs=0.05)


def test_wilson_ci_zero_total() -> None:
    assert _wilson_ci(0, 0) == (0.0, 0.0)


def test_wilson_ci_all_wins() -> None:
    lo, hi = _wilson_ci(100, 100)
    assert hi == pytest.approx(1.0, abs=0.05)


def test_win_rate_by_bucket_correct() -> None:
    buckets = {
        "A": _batch(30, 20),
        "B": _batch(10, 40),
    }
    results = win_rate_by_bucket(buckets)
    assert len(results) == 2
    a = next(r for r in results if r.bucket_label == "A")
    assert a.wins == 30
    assert a.losses == 20
    assert a.win_rate == pytest.approx(0.6)
    assert a.ci_lower < a.win_rate < a.ci_upper


def test_win_rate_by_bucket_empty() -> None:
    assert win_rate_by_bucket({}) == []


def test_chi_squared_test_detects_difference() -> None:
    buckets = {
        "High WR": _batch(40, 10),
        "Low WR": _batch(10, 40),
    }
    result = chi_squared_test(buckets)
    assert result is not None
    chi2, p_val = result
    assert chi2 > 0
    assert p_val < 0.05  # should be significant


def test_chi_squared_test_single_bucket() -> None:
    buckets = {"Only": _batch(20, 10)}
    assert chi_squared_test(buckets) is None


def test_point_biserial_test_correlation() -> None:
    # Higher values → wins, lower → losses
    signals: list[dict[str, Any]] = []
    for i in range(50):
        signals.append(_enriched("TP_HIT", value=80.0 + i))
    for i in range(50):
        signals.append(_enriched("SL_HIT", value=20.0 + i))
    result = point_biserial_test(signals, "value")
    assert result is not None
    corr, p_val = result
    assert corr > 0  # positive correlation
    assert p_val < 0.05


def test_point_biserial_test_insufficient_data() -> None:
    signals = [_enriched("TP_HIT", value=1.0)] * 5
    assert point_biserial_test(signals, "value") is None


# ---------------------------------------------------------------------------
# report.py
# ---------------------------------------------------------------------------


def test_build_univariate_report_categorical() -> None:
    signals = (
        [_enriched("TP_HIT", session="LONDON")] * 35
        + [_enriched("SL_HIT", session="LONDON")] * 15
        + [_enriched("TP_HIT", session="ASIAN")] * 10
        + [_enriched("SL_HIT", session="ASIAN")] * 40
    )
    report = build_univariate_report("session", "str", "fvg-impulse", signals)
    assert report["param_name"] == "session"
    assert report["dtype"] == "categorical"
    assert report["total_signals"] == 100
    assert len(report["buckets"]) == 2


def test_build_univariate_report_numeric() -> None:
    signals = [_enriched("TP_HIT", ratio=float(i)) for i in range(60)]
    signals += [_enriched("SL_HIT", ratio=float(i)) for i in range(60, 120)]
    report = build_univariate_report("ratio", "float", "test", signals)
    assert report["dtype"] == "numeric"
    assert report["total_signals"] == 120


def test_build_summary_overall_win_rate() -> None:
    signals = _batch(60, 40, session="LONDON", ratio=1.0)
    param_defs = [
        {"name": "session", "dtype": "str"},
        {"name": "ratio", "dtype": "float"},
    ]
    result = build_summary("test", signals, param_defs)
    assert result["strategy"] == "test"
    assert result["total_resolved"] == 100
    assert result["win_rate_overall"] == pytest.approx(0.6)
    assert result["params_analyzed"] == 2


def test_build_summary_empty_signals() -> None:
    result = build_summary("test", [], [])
    assert result["total_resolved"] == 0
    assert result["win_rate_overall"] == 0.0
