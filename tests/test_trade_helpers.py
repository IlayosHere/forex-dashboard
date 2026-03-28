"""
tests/test_trade_helpers.py
----------------------------
Unit tests for api/services/trade_helpers.py: calculate_pnl, apply_trade_filters,
trade_to_response.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import TradeModel
from api.services.trade_helpers import (
    apply_trade_filters,
    calculate_pnl,
    trade_to_response,
)
from tests.conftest import make_trade


# ---------------------------------------------------------------------------
# calculate_pnl — forex
# ---------------------------------------------------------------------------


def test_pnl_buy_forex_profit() -> None:
    pips, usd, rr = calculate_pnl(
        symbol="EURUSD", direction="BUY",
        entry_price=1.08000, exit_price=1.08300,
        lot_size=1.0, risk_pips=20.0,
    )
    assert pips == 30.0
    assert usd == 300.0
    assert rr == 1.5


def test_pnl_sell_forex_profit() -> None:
    pips, usd, rr = calculate_pnl(
        symbol="EURUSD", direction="SELL",
        entry_price=1.08300, exit_price=1.08000,
        lot_size=1.0, risk_pips=20.0,
    )
    assert pips == 30.0
    assert usd == 300.0
    assert rr == 1.5


def test_pnl_buy_forex_loss() -> None:
    pips, usd, rr = calculate_pnl(
        symbol="EURUSD", direction="BUY",
        entry_price=1.08300, exit_price=1.08000,
        lot_size=1.0, risk_pips=20.0,
    )
    assert pips == -30.0
    assert usd == -300.0
    assert rr == -1.5


def test_pnl_jpy_pair() -> None:
    pips, usd, rr = calculate_pnl(
        symbol="USDJPY", direction="BUY",
        entry_price=150.000, exit_price=150.200,
        lot_size=1.0, risk_pips=10.0,
    )
    assert pips == 20.0
    expected_pip_val = (100_000 * 0.01) / 150.0
    assert usd == pytest.approx(20.0 * expected_pip_val * 1.0, rel=0.01)


def test_pnl_zero_risk_pips_returns_none_rr() -> None:
    _, _, rr = calculate_pnl(
        symbol="EURUSD", direction="BUY",
        entry_price=1.08000, exit_price=1.08100,
        lot_size=1.0, risk_pips=0.0,
    )
    assert rr is None


# ---------------------------------------------------------------------------
# calculate_pnl — futures
# ---------------------------------------------------------------------------


def test_pnl_buy_futures_profit() -> None:
    pips, usd, rr = calculate_pnl(
        symbol="MNQ", direction="BUY",
        entry_price=20000, exit_price=20050,
        lot_size=2, risk_pips=25.0,
        instrument_type="futures_mnq",
    )
    assert pips == 50.0
    assert usd == 200.0  # 50 * 2.0 * 2
    assert rr == 2.0


def test_pnl_sell_futures_loss() -> None:
    pips, usd, rr = calculate_pnl(
        symbol="MNQ", direction="SELL",
        entry_price=20000, exit_price=20030,
        lot_size=1, risk_pips=25.0,
        instrument_type="futures_mnq",
    )
    assert pips == -30.0
    assert usd == -60.0


# ---------------------------------------------------------------------------
# apply_trade_filters
# ---------------------------------------------------------------------------


def test_filter_by_strategy(db: Session) -> None:
    make_trade(db, strategy="strat-a")
    make_trade(db, strategy="strat-b")
    stmt = select(TradeModel)
    stmt = apply_trade_filters(stmt, strategy="strat-a", symbol=None,
                                status=None, outcome=None,
                                date_from=None, date_to=None)
    results = list(db.scalars(stmt).all())
    assert len(results) == 1
    assert results[0].strategy == "strat-a"


def test_filter_by_date_range(db: Session) -> None:
    early = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    late = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
    make_trade(db, open_time=early)
    make_trade(db, open_time=late)
    stmt = select(TradeModel)
    stmt = apply_trade_filters(
        stmt, strategy=None, symbol=None, status=None, outcome=None,
        date_from=date(2025, 5, 1), date_to=date(2025, 7, 1),
    )
    results = list(db.scalars(stmt).all())
    assert len(results) == 1


def test_filter_no_filters_returns_all(db: Session) -> None:
    make_trade(db)
    make_trade(db)
    stmt = select(TradeModel)
    stmt = apply_trade_filters(stmt, None, None, None, None, None, None)
    results = list(db.scalars(stmt).all())
    assert len(results) == 2


def test_filter_by_instrument_type(db: Session) -> None:
    make_trade(db, instrument_type="forex")
    make_trade(db, instrument_type="futures_mnq")
    stmt = select(TradeModel)
    stmt = apply_trade_filters(
        stmt, None, None, None, None, None, None,
        instrument_type="futures_mnq",
    )
    results = list(db.scalars(stmt).all())
    assert len(results) == 1
    assert results[0].instrument_type == "futures_mnq"


# ---------------------------------------------------------------------------
# trade_to_response
# ---------------------------------------------------------------------------


def test_trade_to_response_serializes_all_fields(db: Session) -> None:
    trade = make_trade(db, status="open")
    result = trade_to_response(trade, {})
    assert result["id"] == trade.id
    assert result["strategy"] == "fvg-impulse"
    assert result["symbol"] == "EURUSD"
    assert result["direction"] == "BUY"
    assert result["account_name"] is None
    assert "trade_metadata" in result
