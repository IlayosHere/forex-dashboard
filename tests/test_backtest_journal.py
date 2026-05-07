"""
tests/test_backtest_journal.py
-------------------------------
Tests for backtest journal: account_type=backtest validation,
criteria_met_at_entry round-trip, exclude_account_type filter on
/api/trades and /api/trades/stats, LEFT JOIN de-duplication, and
null-account-id pass-through.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models import AccountModel, TradeModel
from api.services.trade_filters import StatsFilterParams, TradeFilterParams
from api.services.trade_helpers import apply_trade_filters
from tests.conftest import TEST_USER, make_trade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _account_payload(**overrides: object) -> dict:
    base: dict = {
        "name": "MNQ Backtest",
        "account_type": "backtest",
        "instrument_type": "futures_mnq",
    }
    base.update(overrides)
    return base


def _trade_payload(**overrides: object) -> dict:
    base: dict = {
        "strategy": "ict-mnq",
        "symbol": "MNQ",
        "direction": "BUY",
        "instrument_type": "futures_mnq",
        "entry_price": 20000.0,
        "sl_price": 19975.0,
        "lot_size": 1.0,
        "risk_pips": 25.0,
        "open_time": "2025-12-01T10:30:00Z",
    }
    base.update(overrides)
    return base


def _make_account(db: Session, account_type: str = "backtest") -> AccountModel:
    acct = AccountModel(
        id=str(uuid.uuid4()),
        name=f"{account_type} account",
        account_type=account_type,
        instrument_type="futures_mnq",
        status="active",
        owner=TEST_USER,
        created_at=datetime.now(timezone.utc),
    )
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return acct


def _filters_with_exclude(exclude_account_type: str | None = None) -> TradeFilterParams:
    f = object.__new__(TradeFilterParams)
    f.strategy = None
    f.symbol = None
    f.status = None
    f.outcome = None
    f.instrument_type = None
    f.account_id = None
    f.rule_followed = None
    f.exclude_account_type = exclude_account_type
    f.date_from = None
    f.date_to = None
    return f


def _stats_filters_with_exclude(exclude_account_type: str | None = None) -> StatsFilterParams:
    f = object.__new__(StatsFilterParams)
    f.strategy = None
    f.symbol = None
    f.instrument_type = None
    f.account_id = None
    f.exclude_account_type = exclude_account_type
    f.date_from = None
    f.date_to = None
    return f


# ---------------------------------------------------------------------------
# POST /api/accounts — backtest account_type validation
# ---------------------------------------------------------------------------


def test_create_backtest_account_returns_201(client: TestClient) -> None:
    resp = client.post("/api/accounts", json=_account_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["account_type"] == "backtest"
    assert data["instrument_type"] == "futures_mnq"
    assert data["balance"] is None


def test_create_backtest_account_invalid_type_returns_422(client: TestClient) -> None:
    resp = client.post("/api/accounts", json=_account_payload(account_type="paper"))
    assert resp.status_code == 422


def test_backtest_account_no_balance_required(client: TestClient) -> None:
    resp = client.post("/api/accounts", json=_account_payload())
    assert resp.status_code == 201
    assert resp.json()["balance"] is None


# ---------------------------------------------------------------------------
# POST /api/trades — criteria_met_at_entry round-trip
# ---------------------------------------------------------------------------


def test_create_trade_criteria_met_true(client: TestClient) -> None:
    resp = client.post("/api/trades", json=_trade_payload(criteria_met_at_entry=True))
    assert resp.status_code == 201
    assert resp.json()["criteria_met_at_entry"] is True


def test_create_trade_criteria_met_false(client: TestClient) -> None:
    resp = client.post("/api/trades", json=_trade_payload(criteria_met_at_entry=False))
    assert resp.status_code == 201
    assert resp.json()["criteria_met_at_entry"] is False


def test_create_trade_criteria_met_null_by_default(client: TestClient) -> None:
    resp = client.post("/api/trades", json=_trade_payload())
    assert resp.status_code == 201
    assert resp.json()["criteria_met_at_entry"] is None


def test_update_trade_sets_criteria_met(client: TestClient) -> None:
    trade_id = client.post("/api/trades", json=_trade_payload()).json()["id"]
    resp = client.put(f"/api/trades/{trade_id}", json={"criteria_met_at_entry": True})
    assert resp.status_code == 200
    assert resp.json()["criteria_met_at_entry"] is True


# ---------------------------------------------------------------------------
# apply_trade_filters — exclude_account_type (unit, via DB)
# ---------------------------------------------------------------------------


def test_exclude_backtest_omits_backtest_trades(db: Session) -> None:
    live_acct = _make_account(db, "live")
    bt_acct = _make_account(db, "backtest")
    make_trade(db, account_id=live_acct.id)
    make_trade(db, account_id=bt_acct.id)

    stmt = select(TradeModel).where(TradeModel.owner == TEST_USER)
    stmt = apply_trade_filters(stmt, _filters_with_exclude("backtest"))
    results = list(db.scalars(stmt).all())
    assert len(results) == 1
    assert results[0].account_id == live_acct.id


def test_exclude_backtest_no_duplicates_with_multiple_trades(db: Session) -> None:
    live_acct = _make_account(db, "live")
    bt_acct = _make_account(db, "backtest")
    make_trade(db, account_id=live_acct.id)
    make_trade(db, account_id=live_acct.id)
    make_trade(db, account_id=bt_acct.id)

    stmt = select(TradeModel).where(TradeModel.owner == TEST_USER)
    stmt = apply_trade_filters(stmt, _filters_with_exclude("backtest"))
    results = list(db.scalars(stmt).all())
    assert len(results) == 2


def test_null_account_id_not_excluded_by_exclude_account_type(db: Session) -> None:
    make_trade(db, account_id=None)

    stmt = select(TradeModel).where(TradeModel.owner == TEST_USER)
    stmt = apply_trade_filters(stmt, _filters_with_exclude("backtest"))
    results = list(db.scalars(stmt).all())
    assert len(results) == 1


def test_no_exclude_filter_returns_all(db: Session) -> None:
    bt_acct = _make_account(db, "backtest")
    live_acct = _make_account(db, "live")
    make_trade(db, account_id=bt_acct.id)
    make_trade(db, account_id=live_acct.id)
    make_trade(db, account_id=None)

    stmt = select(TradeModel).where(TradeModel.owner == TEST_USER)
    stmt = apply_trade_filters(stmt, _filters_with_exclude(None))
    results = list(db.scalars(stmt).all())
    assert len(results) == 3


# ---------------------------------------------------------------------------
# GET /api/trades?exclude_account_type=backtest — integration
# ---------------------------------------------------------------------------


def test_api_excludes_backtest_trades_by_default_param(
    client: TestClient, db: Session,
) -> None:
    live_acct = _make_account(db, "live")
    bt_acct = _make_account(db, "backtest")
    make_trade(db, account_id=live_acct.id, instrument_type="futures_mnq")
    make_trade(db, account_id=bt_acct.id, instrument_type="futures_mnq")

    resp = client.get("/api/trades", params={"exclude_account_type": "backtest"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["account_id"] == live_acct.id


def test_api_includes_backtest_when_no_exclude_param(
    client: TestClient, db: Session,
) -> None:
    bt_acct = _make_account(db, "backtest")
    make_trade(db, account_id=bt_acct.id, instrument_type="futures_mnq")

    resp = client.get("/api/trades")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# GET /api/trades/stats?exclude_account_type=backtest — integration
# ---------------------------------------------------------------------------


def test_stats_excludes_backtest_trades(client: TestClient, db: Session) -> None:
    live_acct = _make_account(db, "live")
    bt_acct = _make_account(db, "backtest")
    make_trade(
        db, account_id=live_acct.id, status="closed", outcome="win",
        pnl_pips=20.0, pnl_usd=40.0, rr_achieved=2.0,
        instrument_type="futures_mnq",
    )
    make_trade(
        db, account_id=bt_acct.id, status="closed", outcome="win",
        pnl_pips=50.0, pnl_usd=100.0, rr_achieved=5.0,
        instrument_type="futures_mnq",
    )

    resp = client.get("/api/trades/stats", params={"exclude_account_type": "backtest"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trades"] == 1
    assert data["wins"] == 1
    assert data["total_pnl_usd"] == pytest.approx(40.0)


def test_stats_includes_backtest_when_no_exclude_param(
    client: TestClient, db: Session,
) -> None:
    bt_acct = _make_account(db, "backtest")
    make_trade(
        db, account_id=bt_acct.id, status="closed", outcome="win",
        pnl_pips=50.0, pnl_usd=100.0, rr_achieved=5.0,
        instrument_type="futures_mnq",
    )

    resp = client.get("/api/trades/stats")
    assert resp.status_code == 200
    assert resp.json()["total_trades"] == 1


def test_stats_account_id_filter_backtest_account(
    client: TestClient, db: Session,
) -> None:
    bt_acct = _make_account(db, "backtest")
    live_acct = _make_account(db, "live")
    make_trade(
        db, account_id=bt_acct.id, status="closed", outcome="win",
        pnl_pips=30.0, pnl_usd=60.0, rr_achieved=3.0,
        instrument_type="futures_mnq",
    )
    make_trade(
        db, account_id=live_acct.id, status="closed", outcome="loss",
        pnl_pips=-20.0, pnl_usd=-40.0, rr_achieved=-2.0,
        instrument_type="futures_mnq",
    )

    resp = client.get("/api/trades/stats", params={"account_id": bt_acct.id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trades"] == 1
    assert data["wins"] == 1
    assert data["total_pnl_usd"] == pytest.approx(60.0)
