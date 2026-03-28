"""
tests/test_trade_stats.py
--------------------------
Unit tests for api/services/trade_stats.py metric calculations.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from api.models import TradeModel
from api.services.trade_stats import (
    aggregate_by_field,
    calculate_trade_metrics,
)
from tests.conftest import make_trade


# ---------------------------------------------------------------------------
# calculate_trade_metrics
# ---------------------------------------------------------------------------


def test_metrics_empty_lists_returns_zeros() -> None:
    m = calculate_trade_metrics([], [])
    assert m["total_trades"] == 0
    assert m["wins"] == 0
    assert m["win_rate"] is None
    assert m["total_pnl_pips"] == 0.0
    assert m["current_streak"] == 0
    assert m["profit_factor"] is None


def test_metrics_all_wins(db: Session) -> None:
    base = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
    trades = [
        make_trade(
            db, status="closed", outcome="win",
            pnl_pips=20.0, pnl_usd=100.0, rr_achieved=2.0,
            open_time=base + timedelta(hours=i),
            close_time=base + timedelta(hours=i + 1),
        )
        for i in range(3)
    ]
    m = calculate_trade_metrics(trades, trades)
    assert m["wins"] == 3
    assert m["losses"] == 0
    assert m["win_rate"] == 100.0
    assert m["current_streak"] == 3
    assert m["profit_factor"] is None  # no losses -> None


def test_metrics_all_losses(db: Session) -> None:
    base = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
    trades = [
        make_trade(
            db, status="closed", outcome="loss",
            pnl_pips=-15.0, pnl_usd=-75.0, rr_achieved=-1.0,
            open_time=base + timedelta(hours=i),
            close_time=base + timedelta(hours=i + 1),
        )
        for i in range(2)
    ]
    m = calculate_trade_metrics(trades, trades)
    assert m["wins"] == 0
    assert m["losses"] == 2
    assert m["win_rate"] == 0.0
    assert m["current_streak"] == -2
    assert m["avg_rr"] is None  # no wins → no avg R:R


def test_metrics_mixed_results(db: Session) -> None:
    base = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
    t1 = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=30.0, pnl_usd=150.0, rr_achieved=2.0,
        open_time=base, close_time=base + timedelta(hours=1),
    )
    t2 = make_trade(
        db, status="closed", outcome="loss",
        pnl_pips=-15.0, pnl_usd=-75.0, rr_achieved=-1.0,
        open_time=base + timedelta(hours=2),
        close_time=base + timedelta(hours=3),
    )
    t3 = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=20.0, pnl_usd=100.0, rr_achieved=1.5,
        open_time=base + timedelta(hours=4),
        close_time=base + timedelta(hours=5),
    )
    all_trades = [t1, t2, t3]
    m = calculate_trade_metrics(all_trades, all_trades)
    assert m["wins"] == 2
    assert m["losses"] == 1
    assert m["total_pnl_pips"] == 35.0
    assert m["avg_rr"] == 1.75  # (2.0 + 1.5) / 2 — wins only
    assert m["profit_factor"] == 3.33  # 250 / 75
    assert m["current_streak"] == 1  # last trade is a win


def test_metrics_includes_open_trade_count(db: Session) -> None:
    base = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
    open_t = make_trade(db, status="open", open_time=base)
    closed_t = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=10.0, pnl_usd=50.0,
        open_time=base + timedelta(hours=1),
        close_time=base + timedelta(hours=2),
    )
    m = calculate_trade_metrics([open_t, closed_t], [closed_t])
    assert m["total_trades"] == 2
    assert m["open_trades"] == 1
    assert m["closed_trades"] == 1


# ---------------------------------------------------------------------------
# aggregate_by_field
# ---------------------------------------------------------------------------


def test_aggregate_by_strategy(db: Session) -> None:
    base = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
    make_trade(
        db, strategy="strat-a", status="closed", outcome="win",
        pnl_pips=20.0, open_time=base,
        close_time=base + timedelta(hours=1),
    )
    make_trade(
        db, strategy="strat-a", status="closed", outcome="loss",
        pnl_pips=-10.0, open_time=base + timedelta(hours=2),
        close_time=base + timedelta(hours=3),
    )
    make_trade(
        db, strategy="strat-b", status="closed", outcome="win",
        pnl_pips=15.0, open_time=base + timedelta(hours=4),
        close_time=base + timedelta(hours=5),
    )
    closed = list(db.query(TradeModel).filter_by(status="closed").all())
    result = aggregate_by_field(closed, "strategy")
    assert "strat-a" in result
    assert result["strat-a"]["total"] == 2
    assert result["strat-a"]["wins"] == 1
    assert "strat-b" in result
    assert result["strat-b"]["total"] == 1


def test_aggregate_by_symbol(db: Session) -> None:
    base = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
    make_trade(
        db, symbol="EURUSD", status="closed", outcome="win",
        pnl_pips=10.0, open_time=base,
        close_time=base + timedelta(hours=1),
    )
    make_trade(
        db, symbol="GBPUSD", status="closed", outcome="loss",
        pnl_pips=-5.0, open_time=base + timedelta(hours=2),
        close_time=base + timedelta(hours=3),
    )
    closed = list(db.query(TradeModel).filter_by(status="closed").all())
    result = aggregate_by_field(closed, "symbol")
    assert set(result.keys()) == {"EURUSD", "GBPUSD"}
    assert result["EURUSD"]["win_rate"] == 100.0
    assert result["GBPUSD"]["win_rate"] == 0.0
