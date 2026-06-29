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
from api.services.trade_filters import TradeFilterParams
from api.services.trade_helpers import (
    PnlInput,
    apply_trade_filters,
    calculate_pnl,
    trade_to_response,
)
from tests.conftest import make_trade


def _filters(
    strategy: str | None = None,
    symbol: str | None = None,
    status: str | None = None,
    outcome: str | None = None,
    instrument_type: str | None = None,
    account_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> TradeFilterParams:
    """Build a TradeFilterParams bypassing FastAPI Query defaults."""
    f = object.__new__(TradeFilterParams)
    f.strategy = strategy
    f.symbol = symbol
    f.status = status
    f.outcome = outcome
    f.instrument_type = instrument_type
    f.account_id = account_id
    f.date_from = date_from
    f.date_to = date_to
    return f


def test_pnl_zero_risk_pips_returns_none_rr() -> None:
    _, _, rr = calculate_pnl(PnlInput(
        symbol="MNQ", direction="BUY",
        entry_price=20000, exit_price=20010,
        lot_size=1.0, risk_pips=0.0,
    ))
    assert rr is None


# ---------------------------------------------------------------------------
# calculate_pnl — futures (symbol-based routing, instrument_type="futures")
# ---------------------------------------------------------------------------


def test_pnl_buy_futures_profit() -> None:
    # MNQ: 50 pts * $2/pt * 2 contracts = $200
    pips, usd, rr = calculate_pnl(PnlInput(
        symbol="MNQ", direction="BUY",
        entry_price=20000, exit_price=20050,
        lot_size=2, risk_pips=25.0,
        instrument_type="futures",
    ))
    assert pips == 50.0
    assert usd == 200.0
    assert rr == 2.0


def test_pnl_sell_futures_loss() -> None:
    pips, usd, rr = calculate_pnl(PnlInput(
        symbol="MNQ", direction="SELL",
        entry_price=20000, exit_price=20030,
        lot_size=1, risk_pips=25.0,
        instrument_type="futures",
    ))
    assert pips == -30.0
    assert usd == -60.0


def test_pnl_unrecognized_symbol_falls_back_to_default_multiplier() -> None:
    """Symbols not in the known futures table default to $2/pt."""
    pips, usd, _ = calculate_pnl(PnlInput(
        symbol="NQ", direction="BUY",
        entry_price=20000, exit_price=20010,
        lot_size=1, risk_pips=10.0,
        instrument_type="futures",
    ))
    assert pips == 10.0
    assert usd == 20.0  # 10 pts * $2/pt (default) * 1 contract


# ---------------------------------------------------------------------------
# calculate_pnl — MES (symbol-based, same instrument_type="futures")
# ---------------------------------------------------------------------------


def test_pnl_buy_mes_profit() -> None:
    # MES: 50 pts * $5/pt * 2 contracts = $500
    pips, usd, rr = calculate_pnl(PnlInput(
        symbol="MES", direction="BUY",
        entry_price=5000, exit_price=5050,
        lot_size=2, risk_pips=25.0,
        instrument_type="futures",
    ))
    assert pips == 50.0
    assert usd == 500.0
    assert rr == 2.0


def test_pnl_sell_mes_profit() -> None:
    # MES: 30 pts * $5/pt * 1 contract = $150
    pips, usd, rr = calculate_pnl(PnlInput(
        symbol="MES", direction="SELL",
        entry_price=5030, exit_price=5000,
        lot_size=1, risk_pips=15.0,
        instrument_type="futures",
    ))
    assert pips == 30.0
    assert usd == 150.0
    assert rr == 2.0


def test_pnl_buy_mes_loss() -> None:
    # MES: -20 pts * $5/pt * 1 contract = -$100
    pips, usd, rr = calculate_pnl(PnlInput(
        symbol="MES", direction="BUY",
        entry_price=5050, exit_price=5030,
        lot_size=1, risk_pips=20.0,
        instrument_type="futures",
    ))
    assert pips == -20.0
    assert usd == -100.0
    assert rr == -1.0


def test_pnl_mes_vs_mnq_ratio() -> None:
    """Same move, same contracts: MES P&L is 2.5x larger than MNQ ($5 vs $2/pt)."""
    _, mnq_usd, _ = calculate_pnl(PnlInput(
        symbol="MNQ", direction="BUY",
        entry_price=20000, exit_price=20040,
        lot_size=1, risk_pips=20.0,
        instrument_type="futures",
    ))
    _, mes_usd, _ = calculate_pnl(PnlInput(
        symbol="MES", direction="BUY",
        entry_price=5000, exit_price=5040,
        lot_size=1, risk_pips=20.0,
        instrument_type="futures",
    ))
    assert mes_usd == pytest.approx(mnq_usd * 2.5)


# ---------------------------------------------------------------------------
# apply_trade_filters
# ---------------------------------------------------------------------------


def test_filter_by_strategy(db: Session) -> None:
    make_trade(db, strategy="strat-a")
    make_trade(db, strategy="strat-b")
    stmt = select(TradeModel)
    stmt = apply_trade_filters(stmt, _filters(strategy="strat-a"))
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
        stmt, _filters(date_from=date(2025, 5, 1), date_to=date(2025, 7, 1)),
    )
    results = list(db.scalars(stmt).all())
    assert len(results) == 1


def test_filter_no_filters_returns_all(db: Session) -> None:
    make_trade(db)
    make_trade(db)
    stmt = select(TradeModel)
    stmt = apply_trade_filters(stmt, _filters())
    results = list(db.scalars(stmt).all())
    assert len(results) == 2


def test_filter_by_instrument_type(db: Session) -> None:
    make_trade(db, instrument_type="futures")
    make_trade(db, instrument_type="futures_mnq")
    stmt = select(TradeModel)
    stmt = apply_trade_filters(stmt, _filters(instrument_type="futures_mnq"))
    results = list(db.scalars(stmt).all())
    assert len(results) == 1
    assert results[0].instrument_type == "futures_mnq"


def test_filter_futures_virtual_matches_all_futures(db: Session) -> None:
    """instrument_type='futures' matches canonical 'futures' plus legacy futures_mnq/futures_mes."""
    make_trade(db, instrument_type="futures")        # new canonical
    make_trade(db, instrument_type="futures_mnq")    # legacy
    make_trade(db, instrument_type="futures_mes")    # legacy
    stmt = select(TradeModel)
    stmt = apply_trade_filters(stmt, _filters(instrument_type="futures"))
    results = list(db.scalars(stmt).all())
    assert len(results) == 3
    instrument_types = {r.instrument_type for r in results}
    assert instrument_types == {"futures", "futures_mnq", "futures_mes"}


# ---------------------------------------------------------------------------
# trade_to_response
# ---------------------------------------------------------------------------


def test_trade_to_response_serializes_all_fields(db: Session) -> None:
    trade = make_trade(db, status="open")
    result = trade_to_response(trade, {})
    assert result["id"] == trade.id
    assert result["strategy"] == "mnq-daily"
    assert result["symbol"] == "MNQ"
    assert result["direction"] == "BUY"
    assert result["account_name"] is None
    assert "trade_metadata" in result
