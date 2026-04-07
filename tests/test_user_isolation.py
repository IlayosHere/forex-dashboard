"""
tests/test_user_isolation.py
-----------------------------
Cross-user isolation tests: verifies that trades, accounts, and stats are
scoped to the authenticated user and invisible/inaccessible to others.
Signals are global and must remain visible to all users.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models import AccountModel, SignalModel
from tests.conftest import TEST_USER, TEST_USER_2, make_trade


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _account_payload(**overrides: object) -> dict:
    base: dict = {
        "name": "My Demo",
        "account_type": "demo",
        "instrument_type": "forex",
    }
    base.update(overrides)
    return base


def _insert_account(db: Session, owner: str = TEST_USER) -> AccountModel:
    account = AccountModel(
        id=str(uuid.uuid4()),
        name="Isolation Account",
        account_type="demo",
        instrument_type="forex",
        status="active",
        prop_firm=None,
        phase=None,
        owner=owner,
        created_at=datetime.now(timezone.utc),
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


# ---------------------------------------------------------------------------
# Account isolation
# ---------------------------------------------------------------------------


def test_user_cannot_see_other_users_accounts(
    db: Session, client_other_user: TestClient,
) -> None:
    _insert_account(db, owner=TEST_USER)
    resp = client_other_user.get("/api/accounts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_user_cannot_update_other_users_account(
    db: Session, client_other_user: TestClient,
) -> None:
    account = _insert_account(db, owner=TEST_USER)
    resp = client_other_user.put(f"/api/accounts/{account.id}", json={"name": "Hacked"})
    assert resp.status_code == 404


def test_user_cannot_delete_other_users_account(
    db: Session, client_other_user: TestClient,
) -> None:
    account = _insert_account(db, owner=TEST_USER)
    resp = client_other_user.delete(f"/api/accounts/{account.id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Trade isolation
# ---------------------------------------------------------------------------


def test_user_cannot_see_other_users_trades(
    db: Session, client_other_user: TestClient,
) -> None:
    make_trade(db, owner=TEST_USER)
    resp = client_other_user.get("/api/trades")
    assert resp.status_code == 200
    assert resp.json() == []


def test_user_cannot_get_other_users_trade_by_id(
    db: Session, client_other_user: TestClient,
) -> None:
    trade = make_trade(db, owner=TEST_USER)
    resp = client_other_user.get(f"/api/trades/{trade.id}")
    assert resp.status_code == 404


def test_user_cannot_update_other_users_trade(
    db: Session, client_other_user: TestClient,
) -> None:
    trade = make_trade(db, owner=TEST_USER)
    resp = client_other_user.put(f"/api/trades/{trade.id}", json={"notes": "hacked"})
    assert resp.status_code == 404


def test_user_cannot_delete_other_users_trade(
    db: Session, client_other_user: TestClient,
) -> None:
    trade = make_trade(db, owner=TEST_USER)
    resp = client_other_user.delete(f"/api/trades/{trade.id}")
    assert resp.status_code == 404


def test_user_cannot_link_trade_to_other_users_account(
    db: Session, client_other_user: TestClient,
) -> None:
    account = _insert_account(db, owner=TEST_USER)
    payload = {
        "strategy": "fvg-impulse",
        "symbol": "EURUSD",
        "direction": "BUY",
        "entry_price": 1.085,
        "sl_price": 1.082,
        "lot_size": 0.5,
        "risk_pips": 30.0,
        "open_time": "2025-03-01T12:00:00Z",
        "account_id": account.id,
    }
    resp = client_other_user.post("/api/trades", json=payload)
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Stats isolation
# ---------------------------------------------------------------------------


def test_trade_stats_scoped_to_current_user(
    db: Session, client: TestClient,
) -> None:
    make_trade(db, owner=TEST_USER, status="closed", outcome="win", pnl_usd=100.0)
    make_trade(db, owner=TEST_USER_2, status="closed", outcome="loss", pnl_usd=-50.0)
    resp = client.get("/api/trades/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["wins"] >= 1
    assert data["losses"] == 0


# ---------------------------------------------------------------------------
# Signals are global (visible to all users)
# ---------------------------------------------------------------------------


def test_signals_visible_to_all_users(
    db: Session, client: TestClient, client_other_user: TestClient,
) -> None:
    signal = SignalModel(
        id=str(uuid.uuid4()),
        strategy="fvg-impulse",
        symbol="GBPUSD",
        direction="SELL",
        candle_time=datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
        entry=1.27000,
        sl=1.27300,
        tp=1.26400,
        lot_size=0.5,
        risk_pips=30.0,
        spread_pips=1.5,
        signal_metadata={},
        created_at=datetime.now(timezone.utc),
    )
    db.add(signal)
    db.commit()

    resp_user1 = client.get("/api/signals")
    resp_user2 = client_other_user.get("/api/signals")
    assert resp_user1.status_code == 200
    assert resp_user2.status_code == 200
    items1 = resp_user1.json()["items"] if "items" in resp_user1.json() else resp_user1.json()
    items2 = resp_user2.json()["items"] if "items" in resp_user2.json() else resp_user2.json()
    assert len(items1) == 1
    assert len(items2) == 1
    assert items1[0]["id"] == items2[0]["id"]
