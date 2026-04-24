"""
tests/test_analytics_scoring.py
--------------------------------
Unit tests for analytics/scoring.py — compute_score().
"""
from __future__ import annotations

from analytics.scoring import compute_score, _compute_indicator, _build_explanation


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _confirmed(name: str, delta: float, best_bucket: str) -> dict:
    """Build a minimal confirmed-param row."""
    return {"param_name": name, "delta": delta, "best_bucket": best_bucket}


# ---------------------------------------------------------------------------
# compute_score tests
# ---------------------------------------------------------------------------

def test_score_positive_when_all_edges_matched():
    """All confirmed params return their 'prefer' bucket → score > 0."""
    confirmed = [
        _confirmed("session_label", delta=0.12, best_bucket="NY AM"),
        _confirmed("trend_h1_aligned", delta=0.08, best_bucket="True"),
    ]

    class _FakeSignal:
        strategy = "fvg-impulse"
        symbol = "EURUSD"
        signal_metadata = {}
        candle_time = None

    import unittest.mock as mock

    signal = _FakeSignal()

    with mock.patch(
        "analytics.scoring.resolve_all_params",
        return_value={"session_label": "NY AM", "trend_h1_aligned": "True"},
    ):
        result = compute_score(signal, "fvg-impulse", None, confirmed)

    assert result["score"] > 0
    assert result["max_possible"] > 0
    assert result["score"] == result["max_possible"]


def test_score_negative_when_edges_violated():
    """Confirmed params with delta > 0 but signal in best_bucket when delta < 0 → score < 0."""
    confirmed = [
        _confirmed("session_label", delta=-0.10, best_bucket="NY AM"),
        _confirmed("trend_h1_aligned", delta=-0.06, best_bucket="True"),
    ]

    import unittest.mock as mock

    class _FakeSignal:
        strategy = "fvg-impulse"
        symbol = "EURUSD"
        signal_metadata = {}
        candle_time = None

    signal = _FakeSignal()

    with mock.patch(
        "analytics.scoring.resolve_all_params",
        return_value={"session_label": "NY AM", "trend_h1_aligned": "True"},
    ):
        result = compute_score(signal, "fvg-impulse", None, confirmed)

    assert result["score"] < 0


def test_score_zero_when_no_confirmed_params():
    """Empty confirmed_params list → score=0, max_possible=0."""
    result = compute_score(object(), "fvg-impulse", None, [])

    assert result["score"] == 0
    assert result["max_possible"] == 0
    assert result["contributing"] == []


def test_contributing_only_includes_nonzero_indicators():
    """Neutral params (indicator=0) appear in contributing but with indicator=0,
    while they are included so the caller knows the param was evaluated."""
    confirmed = [
        _confirmed("session_label", delta=0.12, best_bucket="NY AM"),
        _confirmed("trend_h1_aligned", delta=0.08, best_bucket="True"),
    ]

    import unittest.mock as mock

    class _FakeSignal:
        strategy = "fvg-impulse"
        symbol = "EURUSD"
        signal_metadata = {}
        candle_time = None

    signal = _FakeSignal()

    # trend_h1_aligned returns a different bucket → indicator=0
    with mock.patch(
        "analytics.scoring.resolve_all_params",
        return_value={"session_label": "NY AM", "trend_h1_aligned": "False"},
    ):
        result = compute_score(signal, "fvg-impulse", None, confirmed)

    nonzero = [c for c in result["contributing"] if c["indicator"] != 0]
    zero = [c for c in result["contributing"] if c["indicator"] == 0]
    assert len(nonzero) == 1
    assert nonzero[0]["param_name"] == "session_label"
    assert len(zero) == 1
    assert zero[0]["param_name"] == "trend_h1_aligned"


def test_score_explanation_format():
    """explanation matches 'X edge(s) matched, Y violated, Z neutral'."""
    contributing = [
        {"indicator": 1, "weight": 10, "param_name": "a", "bucket": "X"},
        {"indicator": -1, "weight": 8, "param_name": "b", "bucket": "Y"},
        {"indicator": 0, "weight": 5, "param_name": "c", "bucket": "Z"},
    ]
    explanation = _build_explanation(contributing)
    assert explanation == "1 edge(s) matched, 1 violated, 1 neutral"


# ---------------------------------------------------------------------------
# _compute_indicator tests
# ---------------------------------------------------------------------------

def test_indicator_positive_when_value_matches_positive_delta():
    assert _compute_indicator("NY AM", "NY AM", delta=0.10) == 1


def test_indicator_negative_when_value_matches_negative_delta():
    assert _compute_indicator("NY AM", "NY AM", delta=-0.10) == -1


def test_indicator_zero_when_value_does_not_match():
    assert _compute_indicator("London", "NY AM", delta=0.10) == 0


def test_indicator_zero_when_value_is_none():
    assert _compute_indicator(None, "NY AM", delta=0.10) == 0
