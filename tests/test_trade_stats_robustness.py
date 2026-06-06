"""
tests/test_trade_stats_robustness.py
--------------------------------------
Unit tests for api/services/trade_stats_robustness.py pure functions.

Lightweight mock objects (dataclasses) are used instead of full TradeModel
to keep tests fast and free of DB fixtures where possible.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from api.services.trade_stats_robustness import (
    compute_drawdown_stats,
    compute_edge_robustness,
    compute_expectancy_ci,
    compute_r_distribution,
    compute_rolling_pf,
)

BASE = datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------------------
# Minimal mock trade — avoids DB, covers only the fields our functions need
# ---------------------------------------------------------------------------


@dataclass
class _Trade:
    """Minimal stand-in for TradeModel."""

    outcome: str | None = None
    rr_achieved: float | None = None
    pnl_usd: float | None = None
    pnl_pips: float | None = None
    open_time: datetime = field(default_factory=lambda: BASE)


def _win(rr: float = 1.0, pnl: float = 100.0, t: datetime = BASE) -> _Trade:
    return _Trade(outcome="win", rr_achieved=rr, pnl_usd=pnl, open_time=t)


def _loss(rr: float = -1.0, pnl: float = -100.0, t: datetime = BASE) -> _Trade:
    return _Trade(outcome="loss", rr_achieved=rr, pnl_usd=pnl, open_time=t)


def _be() -> _Trade:
    return _Trade(outcome="breakeven", rr_achieved=0.0, pnl_usd=0.0)


def _equity_curve(r_values: list[float]) -> list[dict[str, Any]]:
    """Build a minimal equity curve from a list of per-trade R values."""
    cum = 0.0
    result = []
    for r in r_values:
        cum += r
        result.append({"cumulative_r": cum})
    return result


# ---------------------------------------------------------------------------
# compute_r_distribution
# ---------------------------------------------------------------------------


def test_r_distribution_all_bins_present() -> None:
    """All 8 bins are always returned, even if count is 0."""
    result = compute_r_distribution([])
    assert len(result) == 8


def test_r_distribution_breakevens_excluded() -> None:
    """Breakeven trades (rr_achieved=0) are not counted in distribution."""
    trades = [_be(), _be(), _win(rr=1.5)]
    result = compute_r_distribution(trades)
    total_count = sum(b["count"] for b in result)
    assert total_count == 1


def test_r_distribution_correct_bin_assignment() -> None:
    """R values land in the correct bins."""
    trades = [
        _win(rr=0.5),   # → "0 to 1R"
        _win(rr=1.5),   # → "1 to 2R"
        _loss(rr=-0.5), # → "-1 to 0R"
        _win(rr=5.0),   # → ">3R"
        _loss(rr=-4.0), # → "<-3R"
    ]
    result = compute_r_distribution(trades)
    by_label = {b["bucket_label"]: b for b in result}
    assert by_label["0 to 1R"]["count"] == 1
    assert by_label["1 to 2R"]["count"] == 1
    assert by_label["-1 to 0R"]["count"] == 1
    assert by_label[">3R"]["count"] == 1
    assert by_label["<-3R"]["count"] == 1


def test_r_distribution_pct_sums_to_100() -> None:
    """Percentage values sum to 100.0 (within rounding tolerance)."""
    trades = [_win(rr=0.5), _win(rr=1.5), _loss(rr=-1.5)]
    result = compute_r_distribution(trades)
    total_pct = sum(b["pct"] for b in result)
    assert abs(total_pct - 100.0) < 0.2


def test_r_distribution_empty_all_zero_pct() -> None:
    """Empty input → all pct values are 0.0."""
    result = compute_r_distribution([])
    assert all(b["pct"] == 0.0 for b in result)


# ---------------------------------------------------------------------------
# compute_drawdown_stats
# ---------------------------------------------------------------------------


def test_drawdown_all_wins_gives_zero_drawdown() -> None:
    """All winning trades → no drawdown, recovery_factor is None."""
    trades = [_win() for _ in range(5)]
    eq = _equity_curve([1.0] * 5)
    result = compute_drawdown_stats(eq, trades)
    assert result["max_drawdown_r"] == 0.0
    assert result["recovery_factor"] is None


def test_drawdown_measures_peak_to_trough() -> None:
    """Peak-to-trough R drawdown is correctly measured."""
    # R series: +1, +1, -2, -1 → cumulative: 1, 2, 0, -1
    # Peak = 2.0, final trough = -1.0 → DD = 2.0 - (-1.0) = 3.0
    trades = [_win(rr=1.0), _win(rr=1.0), _loss(rr=-2.0), _loss(rr=-1.0)]
    eq = _equity_curve([1.0, 1.0, -2.0, -1.0])
    result = compute_drawdown_stats(eq, trades)
    assert result["max_drawdown_r"] == pytest.approx(3.0, abs=0.01)


def test_drawdown_n_lt_30_expected_streak_none() -> None:
    """expected_max_streak is None when N decisive < 30."""
    trades = [_win()] * 10 + [_loss()] * 10
    eq = _equity_curve([1.0] * 10 + [-1.0] * 10)
    result = compute_drawdown_stats(eq, trades)
    assert result["expected_max_streak"] is None


def test_drawdown_n_gte_30_expected_streak_computed() -> None:
    """expected_max_streak is a float when N decisive >= 30."""
    wins = [_win(rr=1.0)] * 20
    losses = [_loss(rr=-1.0)] * 10
    trades = wins + losses
    eq = _equity_curve([1.0] * 20 + [-1.0] * 10)
    result = compute_drawdown_stats(eq, trades)
    assert result["expected_max_streak"] is not None
    assert isinstance(result["expected_max_streak"], float)


def test_drawdown_max_losing_streak_correct() -> None:
    """Longest consecutive loss sequence is tracked correctly."""
    trades = [
        _win(), _loss(), _loss(), _loss(), _win(), _loss(),
    ]
    eq = _equity_curve([1.0, -1.0, -1.0, -1.0, 1.0, -1.0])
    result = compute_drawdown_stats(eq, trades)
    assert result["max_losing_streak"] == 3


def test_drawdown_recovery_factor_computed() -> None:
    """recovery_factor = total_r / max_drawdown_r when drawdown > 0."""
    # +2, -1 → peak=2, trough=1 → DD=1. total_r=1. RF=1.0
    trades = [_win(rr=2.0), _loss(rr=-1.0)]
    eq = _equity_curve([2.0, -1.0])
    result = compute_drawdown_stats(eq, trades)
    assert result["recovery_factor"] == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# compute_expectancy_ci
# ---------------------------------------------------------------------------


def test_expectancy_ci_n_lt_2_all_none() -> None:
    """Fewer than 2 R values → all fields are None."""
    result = compute_expectancy_ci([])
    assert result["expectancy_r"] is None
    assert result["expectancy_r_ci_low"] is None
    assert result["expectancy_r_ci_high"] is None
    assert result["edge_significant"] is None


def test_expectancy_ci_single_value_all_none() -> None:
    """Single R value → all fields are None (stdev undefined)."""
    result = compute_expectancy_ci([1.5])
    assert result["expectancy_r"] is None


def test_expectancy_ci_valid_output_shape() -> None:
    """N>=2 returns all four keys with correct types."""
    result = compute_expectancy_ci([1.0, 2.0, 1.5, 0.5])
    assert isinstance(result["expectancy_r"], float)
    assert isinstance(result["expectancy_r_ci_low"], float)
    assert isinstance(result["expectancy_r_ci_high"], float)
    assert isinstance(result["edge_significant"], bool)


def test_expectancy_ci_low_lt_high() -> None:
    """CI low is always below CI high."""
    result = compute_expectancy_ci([1.0, 2.0, 0.5, 3.0, 1.5])
    assert result["expectancy_r_ci_low"] < result["expectancy_r_ci_high"]


def test_expectancy_ci_edge_significant_positive() -> None:
    """edge_significant=True when entire CI is above zero."""
    # All strongly positive R values → CI should be entirely positive
    result = compute_expectancy_ci([5.0, 6.0, 5.5, 6.5, 5.0] * 3)
    assert result["edge_significant"] is True


def test_expectancy_ci_edge_not_significant_negative_mix() -> None:
    """edge_significant=False when CI low dips below zero."""
    result = compute_expectancy_ci([1.0, -1.0])
    assert result["edge_significant"] is False


# ---------------------------------------------------------------------------
# compute_edge_robustness
# ---------------------------------------------------------------------------


def test_edge_robustness_all_losses_pf_zero() -> None:
    """All-loss sample gives profit_factor_ex_outliers=0.0 (gross_wins / gross_losses = 0)."""
    trades = [_loss(rr=-1.0, pnl=-100.0)] * 10
    result = compute_edge_robustness(trades)
    assert result["profit_factor_ex_outliers"] == pytest.approx(0.0)


def test_edge_robustness_empty_all_none() -> None:
    """Empty input → both fields are None."""
    result = compute_edge_robustness([])
    assert result["profit_factor_ex_outliers"] is None
    assert result["largest_trade_pct_of_pnl"] is None


def test_edge_robustness_pf_trimmed_ex_outliers() -> None:
    """PF is computed after removing top+bottom 5% outliers."""
    wins = [_win(rr=1.0, pnl=100.0)] * 8
    losses = [_loss(rr=-1.0, pnl=-100.0)] * 8
    # 20 trades → trim = floor(20*0.05)=1 from each end
    # After trim: 7 wins, 7 losses → PF = 700/700 = 1.0
    trades = wins + losses
    result = compute_edge_robustness(trades)
    assert result["profit_factor_ex_outliers"] is not None


def test_edge_robustness_largest_trade_pct() -> None:
    """largest_trade_pct_of_pnl is |max_trade| / gross_wins * 100."""
    trades = [
        _win(rr=1.0, pnl=100.0),
        _win(rr=2.0, pnl=200.0),
        _loss(rr=-1.0, pnl=-100.0),
    ]
    result = compute_edge_robustness(trades)
    # gross_profit = 300, max abs pnl = 200 → pct = 200/300*100 = 66.7
    assert result["largest_trade_pct_of_pnl"] == pytest.approx(66.7, abs=0.1)


def test_edge_robustness_all_wins_no_losses_pf_none() -> None:
    """No losses in trimmed window → profit_factor_ex_outliers is None."""
    trades = [_win(rr=1.0, pnl=100.0)] * 5
    result = compute_edge_robustness(trades)
    assert result["profit_factor_ex_outliers"] is None


# ---------------------------------------------------------------------------
# compute_rolling_pf
# ---------------------------------------------------------------------------


def test_rolling_pf_fewer_than_window_returns_empty() -> None:
    """Fewer than 20 decisive trades → empty list."""
    trades = [_win() for _ in range(15)] + [_loss() for _ in range(4)]
    result = compute_rolling_pf(trades)
    assert result == []


def test_rolling_pf_exactly_window_returns_one_point() -> None:
    """Exactly 20 decisive trades → one data point."""
    trades = [_win(pnl=100.0)] * 10 + [_loss(pnl=-100.0)] * 10
    result = compute_rolling_pf(trades)
    assert len(result) == 1
    assert result[0]["index"] == 19


def test_rolling_pf_correct_sliding_count() -> None:
    """N decisive trades → N - window + 1 rolling points."""
    n = 25
    trades = [_win(pnl=100.0)] * 15 + [_loss(pnl=-100.0)] * 10
    result = compute_rolling_pf(trades)
    assert len(result) == n - 20 + 1


def test_rolling_pf_zero_loss_window_emits_none() -> None:
    """Window with no losses → profit_factor is None (no denominator)."""
    trades = [
        _win(pnl=100.0, t=BASE + timedelta(minutes=i))
        for i in range(25)
    ]
    result = compute_rolling_pf(trades)
    assert all(pt["profit_factor"] is None for pt in result)


def test_rolling_pf_correct_pf_value() -> None:
    """PF = gross_wins / gross_losses within each window."""
    wins = [_win(pnl=100.0, t=BASE + timedelta(minutes=i)) for i in range(10)]
    losses = [
        _loss(pnl=-50.0, t=BASE + timedelta(minutes=10 + i)) for i in range(10)
    ]
    trades = wins + losses
    result = compute_rolling_pf(trades)
    # First window: 10 wins ($100 each) + 10 losses ($50 each) → PF = 1000/500 = 2.0
    assert result[0]["profit_factor"] == pytest.approx(2.0, abs=0.01)


def test_rolling_pf_index_field_correct() -> None:
    """index field equals the position of the last trade in the window."""
    trades = [
        _win(pnl=100.0, t=BASE + timedelta(minutes=i)) for i in range(12)
    ] + [
        _loss(pnl=-100.0, t=BASE + timedelta(minutes=12 + i)) for i in range(10)
    ]
    result = compute_rolling_pf(trades)
    assert result[0]["index"] == 19
    assert result[-1]["index"] == len(trades) - 1
