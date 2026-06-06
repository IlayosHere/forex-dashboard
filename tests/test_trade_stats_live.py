"""
tests/test_trade_stats_live.py
------------------------------
Unit tests for api/services/trade_stats_live.py pure functions:
compute_drawdown, compute_rolling_expectancy, and compute_tp_capture.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from api.services.trade_stats_extended import build_equity_curve
from api.services.trade_stats_live import (
    compute_drawdown,
    compute_rolling_expectancy,
    compute_tp_capture,
)
from tests.conftest import make_trade

BASE = datetime(2025, 3, 3, 10, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# compute_drawdown
# ---------------------------------------------------------------------------


def test_all_profitable_no_drawdown(db: Session) -> None:
    """Three winning trades with positive pnl_usd produce zero drawdown."""
    t1 = make_trade(db, status="closed", outcome="win", pnl_usd=50.0, rr_achieved=1.0,
                    open_time=BASE)
    t2 = make_trade(db, status="closed", outcome="win", pnl_usd=80.0, rr_achieved=2.0,
                    open_time=BASE + timedelta(hours=1))
    t3 = make_trade(db, status="closed", outcome="win", pnl_usd=40.0, rr_achieved=1.0,
                    open_time=BASE + timedelta(hours=2))
    curve = build_equity_curve([t1, t2, t3])
    result = compute_drawdown(curve)

    assert result["max_drawdown_usd"] == 0.0
    assert result["max_drawdown_r"] == 0.0
    assert result["recovery_factor"] is None


def test_current_drawdown_computed_from_last_point(db: Session) -> None:
    """Win then loss: peak at 100, end at 40 — drawdown is 60 USD."""
    t_win = make_trade(db, status="closed", outcome="win", pnl_usd=100.0,
                       rr_achieved=2.0, open_time=BASE)
    t_loss = make_trade(db, status="closed", outcome="loss", pnl_usd=-60.0,
                        rr_achieved=-1.0, open_time=BASE + timedelta(hours=1))
    curve = build_equity_curve([t_win, t_loss])
    result = compute_drawdown(curve)

    assert result["max_drawdown_usd"] == 60.0
    assert result["current_drawdown_usd"] == 60.0
    assert result["current_drawdown_pct"] == pytest.approx(60.0, abs=0.1)
    assert result["drawdown_trade_count"] == 1
    assert result["recovery_factor"] is not None
    assert result["recovery_factor"] == pytest.approx(40.0 / 60.0, abs=0.001)


def test_empty_equity_curve_returns_zeros() -> None:
    """compute_drawdown([]) returns all-zero dict with recovery_factor None."""
    result = compute_drawdown([])

    assert result["max_drawdown_usd"] == 0.0
    assert result["max_drawdown_r"] == 0.0
    assert result["current_drawdown_usd"] == 0.0
    assert result["current_drawdown_pct"] == 0.0
    assert result["drawdown_trade_count"] == 0
    assert result["recovery_factor"] is None


# ---------------------------------------------------------------------------
# compute_rolling_expectancy
# ---------------------------------------------------------------------------


def test_fewer_than_window_returns_empty(db: Session) -> None:
    """Fewer qualifying trades than window size produces an empty list."""
    for i in range(5):
        make_trade(db, status="closed", outcome="win", rr_achieved=1.5,
                   open_time=BASE + timedelta(hours=i))
    trades = [
        make_trade(db, status="closed", outcome="win", rr_achieved=1.5,
                   open_time=BASE + timedelta(hours=i))
        for i in range(5)
    ]
    result = compute_rolling_expectancy(trades, window=30)

    assert result == []


def test_mean_rr_computed_correctly_with_signed_values(db: Session) -> None:
    """Window of exactly 5 trades: mean([2.0, -1.0, 1.5, -1.0, 2.0]) == 0.7."""
    rr_values = [2.0, -1.0, 1.5, -1.0, 2.0]
    trades = [
        make_trade(db, status="closed", outcome="win" if rr >= 0 else "loss",
                   rr_achieved=rr, open_time=BASE + timedelta(hours=i))
        for i, rr in enumerate(rr_values)
    ]
    result = compute_rolling_expectancy(trades, window=5)

    assert len(result) == 1
    assert result[0]["rolling_expectancy_r"] == pytest.approx(0.7, abs=0.01)


def test_trades_without_rr_are_excluded(db: Session) -> None:
    """Open trades with rr_achieved=None are filtered out; only 5 qualify."""
    open_trades = [
        make_trade(db, status="open", outcome=None, rr_achieved=None,
                   open_time=BASE + timedelta(hours=i))
        for i in range(3)
    ]
    closed_trades = [
        make_trade(db, status="closed", outcome="win", rr_achieved=1.0,
                   open_time=BASE + timedelta(hours=i + 3))
        for i in range(5)
    ]
    result = compute_rolling_expectancy(open_trades + closed_trades, window=5)

    assert len(result) == 1


def test_breakeven_trades_included(db: Session) -> None:
    """Trades with rr_achieved=0.0 are not filtered — included in window."""
    trades = [
        make_trade(db, status="closed", outcome="breakeven", rr_achieved=0.0,
                   open_time=BASE + timedelta(hours=i))
        for i in range(5)
    ]
    result = compute_rolling_expectancy(trades, window=5)

    assert result != []
    assert len(result) == 1


# ---------------------------------------------------------------------------
# compute_tp_capture
# ---------------------------------------------------------------------------


def test_null_tp_price_skipped(db: Session) -> None:
    """Winning trade with tp_price=None is excluded; only the valid one counts."""
    make_trade(db, status="closed", outcome="win",
               entry_price=1.08500, tp_price=None, exit_price=1.09100,
               direction="BUY")
    t_valid = make_trade(db, status="closed", outcome="win",
                         entry_price=1.08500, tp_price=1.09100, exit_price=1.09100,
                         direction="BUY")
    result = compute_tp_capture([t_valid])

    assert result["tp_capture_sample_size"] == 1
    assert result["avg_tp_capture_pct"] == pytest.approx(100.0, abs=0.1)


def test_capture_above_100_preserved(db: Session) -> None:
    """Exit beyond TP (150% capture) is preserved without capping."""
    trade = make_trade(db, status="closed", outcome="win",
                       entry_price=1.08500, tp_price=1.09100, exit_price=1.09400,
                       direction="BUY")
    result = compute_tp_capture([trade])

    assert result["avg_tp_capture_pct"] == pytest.approx(150.0, abs=0.1)


def test_no_winners_returns_none(db: Session) -> None:
    """Only loss trades produce avg_tp_capture_pct=None and sample_size=0."""
    t1 = make_trade(db, status="closed", outcome="loss",
                    entry_price=1.08500, tp_price=1.09100, exit_price=1.08200,
                    direction="BUY")
    t2 = make_trade(db, status="closed", outcome="loss",
                    entry_price=1.08500, tp_price=1.09100, exit_price=1.08100,
                    direction="BUY")
    result = compute_tp_capture([t1, t2])

    assert result["avg_tp_capture_pct"] is None
    assert result["tp_capture_sample_size"] == 0


def test_sell_formula_correctness(db: Session) -> None:
    """SELL trade exiting exactly at TP gives 100% capture."""
    trade = make_trade(db, status="closed", outcome="win",
                       entry_price=1.09100, tp_price=1.08500, exit_price=1.08500,
                       direction="SELL")
    result = compute_tp_capture([trade])

    assert result["avg_tp_capture_pct"] == pytest.approx(100.0, abs=0.1)
