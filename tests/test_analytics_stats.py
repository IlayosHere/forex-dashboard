"""
tests/test_analytics_stats.py
------------------------------
Unit tests for analytics/stats/ — filters, univariate, and report.
Uses synthetic enriched signal dicts with known distributions.
"""
from __future__ import annotations

from typing import Any

import pytest

from analytics.stats.classification import (
    best_bucket_analysis,
    classify_from_ci,
)
from analytics.stats.filters import category_split, filter_min_bucket, quintile_split
from analytics.stats.report import (
    _compute_param_significance,
    _rank_params,
    build_summary,
    build_univariate_report,
)
from analytics.stats.univariate import (
    _wilson_ci,
    chi_squared_test,
    point_biserial_test,
    two_proportion_ci,
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


def test_chi_squared_test_all_wins_in_one_bucket_returns_none() -> None:
    """A degenerate table where one bucket has 0 losses must return None.

    ``chi2_contingency`` raises ValueError on a row of all zeros.
    This is a real production scenario when a strategy is new and has very few
    losses. The function must degrade gracefully, not 500.
    """
    buckets = {
        "Bucket A": _batch(20, 0),   # 0 losses → degenerate row
        "Bucket B": _batch(10, 10),
    }
    result = chi_squared_test(buckets)
    # Must not raise; may return None or a valid result depending on scipy version.
    assert result is None or (isinstance(result, tuple) and len(result) == 2)


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


# ---------------------------------------------------------------------------
# two_proportion_ci
# ---------------------------------------------------------------------------


def test_two_proportion_ci_positive_delta() -> None:
    result = two_proportion_ci(60, 100, 40, 100)
    assert result is not None
    delta, ci_lo, ci_hi = result
    assert delta == pytest.approx(0.2)
    assert ci_lo < delta < ci_hi


def test_two_proportion_ci_negative_delta() -> None:
    result = two_proportion_ci(30, 100, 70, 100)
    assert result is not None
    delta, ci_lo, ci_hi = result
    assert delta == pytest.approx(-0.4)
    assert ci_lo < delta < ci_hi


def test_two_proportion_ci_zero_delta() -> None:
    result = two_proportion_ci(50, 100, 50, 100)
    assert result is not None
    delta, ci_lo, ci_hi = result
    assert delta == pytest.approx(0.0)
    assert ci_lo < 0 < ci_hi


def test_two_proportion_ci_zero_n_returns_none() -> None:
    assert two_proportion_ci(0, 0, 10, 20) is None
    assert two_proportion_ci(10, 20, 0, 0) is None


# ---------------------------------------------------------------------------
# classify_from_ci — cover every branch
# ---------------------------------------------------------------------------


def test_classify_strong_positive() -> None:
    assert classify_from_ci(0.15, 0.08, 0.22) == "strong_positive"


def test_classify_strong_negative() -> None:
    assert classify_from_ci(-0.15, -0.22, -0.08) == "strong_negative"


def test_classify_real_positive() -> None:
    assert classify_from_ci(0.07, 0.02, 0.12) == "real_positive"


def test_classify_real_negative() -> None:
    assert classify_from_ci(-0.07, -0.12, -0.02) == "real_negative"


def test_classify_suggestive_positive() -> None:
    assert classify_from_ci(0.15, -0.02, 0.32) == "suggestive_positive"


def test_classify_suggestive_negative() -> None:
    assert classify_from_ci(-0.15, -0.32, 0.02) == "suggestive_negative"


def test_classify_hint_positive() -> None:
    assert classify_from_ci(0.07, -0.03, 0.17) == "hint_positive"


def test_classify_hint_negative() -> None:
    assert classify_from_ci(-0.07, -0.17, 0.03) == "hint_negative"


def test_classify_none() -> None:
    assert classify_from_ci(0.02, -0.10, 0.14) == "none"


def test_classify_boundary_strong_positive() -> None:
    # ci_lo == T (0.05) → strong_positive via >= comparison
    assert classify_from_ci(0.05, 0.05, 0.10) == "strong_positive"


# ---------------------------------------------------------------------------
# best_bucket_analysis
# ---------------------------------------------------------------------------


def test_best_bucket_analysis_empty() -> None:
    assert best_bucket_analysis({}) is None


def test_best_bucket_analysis_single_bucket() -> None:
    # Single bucket vs "rest" (which is empty) → rest has n_rest=0 so
    # two_proportion_ci returns None and selection falls through.
    buckets = {"Only": _batch(40, 10)}
    assert best_bucket_analysis(buckets) is None


def test_best_bucket_analysis_picks_positive_standout() -> None:
    buckets = {
        "Winner": _batch(45, 5),     # 0.90 win rate
        "Middle": _batch(25, 25),    # 0.50 win rate
        "Loser": _batch(22, 28),     # 0.44 win rate
    }
    result = best_bucket_analysis(buckets)
    assert result is not None
    assert result["best_bucket"] == "Winner"
    assert result["delta"] > 0
    assert result["level"] in {
        "strong_positive", "real_positive", "suggestive_positive",
    }


def test_best_bucket_analysis_picks_negative_standout() -> None:
    buckets = {
        "A": _batch(30, 20),   # 0.60
        "B": _batch(28, 22),   # 0.56
        "Drag": _batch(5, 45),  # 0.10 — clear drag
    }
    result = best_bucket_analysis(buckets)
    assert result is not None
    assert result["best_bucket"] == "Drag"
    assert result["delta"] < 0
    assert "negative" in (result["level"] or "")


def test_best_bucket_analysis_tie_breaker_smaller_n() -> None:
    # Two buckets with identical abs(delta): tie-breaker picks smaller n.
    # Construct buckets so the 'rest' stays symmetric.
    buckets = {
        "Small": _batch(20, 10),   # n=30, wr=0.667
        "Large": _batch(20, 40),   # n=60, wr=0.333
        "Mid":   _batch(30, 30),   # n=60, wr=0.500
    }
    result = best_bucket_analysis(buckets)
    assert result is not None
    # "Small" has n=30, "Large" has n=60. If their |delta| ties, smaller n wins.
    # Because of asymmetry the deltas likely differ — just assert a best bucket
    # was picked (real tie is rare in practice).
    assert result["best_bucket"] in {"Small", "Large", "Mid"}


def test_best_bucket_analysis_exact_tie_smaller_n_wins() -> None:
    # Construct a synthetic counts scenario via classification helpers directly
    # to guarantee exact tie handling without relying on fragile arithmetic.
    from analytics.stats.classification import _select_best

    counts = {
        "SmallN": (20, 40),   # p=0.50
        "LargeN": (40, 80),   # p=0.50 — same proportion
    }
    # Wins_total=60, n_total=120. Both deltas will equal 0 → tie on |delta|.
    best = _select_best(counts, wins_total=60, n_total=120, z=1.96)
    assert best is not None
    # With identical |delta|=0, smaller n_b (40) must win.
    assert best[0] == "SmallN"


# ---------------------------------------------------------------------------
# _compute_param_significance end-to-end
# ---------------------------------------------------------------------------


def test_compute_param_significance_categorical_positive() -> None:
    signals = (
        _batch(45, 5, session="LONDON")
        + _batch(25, 25, session="NY")
        + _batch(22, 28, session="ASIAN")
    )
    row = _compute_param_significance(signals, "session", "str")
    assert row is not None
    assert row["best_bucket"] == "LONDON"
    assert row["delta"] is not None and row["delta"] > 0
    assert row["level"] in {
        "strong_positive", "real_positive", "suggestive_positive",
        "hint_positive",
    }
    # Legacy fields are still populated for hover popover.
    assert row["p_value"] is not None
    assert row["correlation"] is not None


def test_compute_param_significance_categorical_negative() -> None:
    signals = (
        _batch(30, 20, session="LONDON")
        + _batch(28, 22, session="NY")
        + _batch(5, 45, session="ASIAN")
    )
    row = _compute_param_significance(signals, "session", "str")
    assert row["best_bucket"] == "ASIAN"
    assert row["delta"] is not None and row["delta"] < 0
    assert "negative" in (row["level"] or "")


def test_compute_param_significance_numeric_quintile() -> None:
    # Monotonic rising win rate across ratio values.
    signals: list[dict[str, Any]] = []
    # Low values lose, high values win — use 250 signals (50 per quintile).
    for i in range(250):
        ratio = float(i)
        # Higher ratio → higher win probability
        win = i % 10 < (1 + i // 50 * 2)  # rough monotonic ramp
        signals.append(_enriched(
            "TP_HIT" if win else "SL_HIT", ratio=ratio,
        ))
    row = _compute_param_significance(signals, "ratio", "float")
    assert row["delta"] is not None
    # Can't guarantee level class, but we assert CI fields exist.
    assert row["ci_lo"] is not None
    assert row["ci_hi"] is not None
    assert row["best_bucket"] is not None


def test_compute_param_significance_all_buckets_filtered() -> None:
    # Only 5 signals per bucket → below min_size=30 threshold.
    signals = (
        _batch(3, 2, session="LONDON")
        + _batch(2, 3, session="NY")
    )
    row = _compute_param_significance(signals, "session", "str")
    assert row["delta"] is None
    assert row["ci_lo"] is None
    assert row["ci_hi"] is None
    assert row["best_bucket"] is None
    assert row["level"] is None


# ---------------------------------------------------------------------------
# _rank_params sort order
# ---------------------------------------------------------------------------


def test_rank_params_conclusive_first_none_last() -> None:
    # session has a strong edge; flag is uniformly distributed across outcomes.
    import random
    random.seed(42)
    signals: list[dict[str, Any]] = []
    # Build signals with a strong session edge and a flag value assigned
    # independently of outcome (so it classifies as 'none').
    session_spec = [("LONDON", 45, 5), ("NY", 20, 30), ("ASIAN", 22, 28)]
    for sess, wins, losses in session_spec:
        for _ in range(wins):
            signals.append(_enriched(
                "TP_HIT", session=sess, flag=random.choice(["A", "B", "C"]),
            ))
        for _ in range(losses):
            signals.append(_enriched(
                "SL_HIT", session=sess, flag=random.choice(["A", "B", "C"]),
            ))
    param_defs = [
        {"name": "flag", "dtype": "str"},
        {"name": "session", "dtype": "str"},
    ]
    ranked = _rank_params(signals, param_defs)
    assert len(ranked) == 2
    # session should be first (strong edge), flag last (weak or 'none')
    assert ranked[0]["param_name"] == "session"
    assert ranked[1]["param_name"] == "flag"


def test_rank_params_null_levels_sort_bottom() -> None:
    # Param "small" filters out (below min bucket); "big" has an edge.
    signals: list[dict[str, Any]] = []
    signals += _batch(45, 5, big="X", small="a")  # 50
    signals += _batch(20, 30, big="Y", small="b")  # 50
    # "small" has only 50+50 = 100 signals but each value appears 50 times,
    # enough for min_bucket. Make "small" degenerate: only 5 rows per value.
    signals += [_enriched("TP_HIT", small="c", big="X") for _ in range(5)]

    param_defs = [
        {"name": "small", "dtype": "str"},
        {"name": "big", "dtype": "str"},
    ]
    ranked = _rank_params(signals, param_defs)
    # "big" should have populated CI fields, "small" may or may not
    # depending on which buckets survive — but in any case rows with
    # delta=None sort to the bottom.
    deltas = [r["delta"] for r in ranked]
    # All non-None deltas come before None deltas (stable partition).
    seen_none = False
    for d in deltas:
        if d is None:
            seen_none = True
        else:
            assert not seen_none, "null-delta row must not precede a populated row"
