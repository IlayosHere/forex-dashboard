"""
tests/test_trades_api.py
-------------------------
Integration tests for /api/trades endpoints.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models import SignalModel
from tests.conftest import make_trade


def _trade_payload(**overrides: object) -> dict:
    """Return a valid TradeCreateRequest body with optional overrides."""
    base: dict = {
        "strategy": "fvg-impulse",
        "symbol": "EURUSD",
        "direction": "BUY",
        "entry_price": 1.08500,
        "sl_price": 1.08200,
        "tp_price": 1.09100,
        "lot_size": 0.50,
        "risk_pips": 30.0,
        "open_time": "2025-03-01T12:00:00Z",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# POST /api/trades
# ---------------------------------------------------------------------------


def test_create_trade_returns_201(client: TestClient) -> None:
    resp = client.post("/api/trades", json=_trade_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["strategy"] == "fvg-impulse"
    assert data["status"] == "open"
    assert data["outcome"] is None


def test_create_trade_invalid_direction_returns_422(client: TestClient) -> None:
    resp = client.post("/api/trades", json=_trade_payload(direction="LONG"))
    assert resp.status_code == 422


def test_create_trade_with_account(
    client: TestClient, sample_account: object,
) -> None:
    from api.models import AccountModel
    acct: AccountModel = sample_account  # type: ignore[assignment]
    resp = client.post("/api/trades", json=_trade_payload(account_id=acct.id))
    assert resp.status_code == 201
    assert resp.json()["account_id"] == acct.id
    assert resp.json()["account_name"] == "Test Demo"


def test_create_trade_missing_account_returns_404(client: TestClient) -> None:
    resp = client.post(
        "/api/trades", json=_trade_payload(account_id="nonexistent"),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/trades
# ---------------------------------------------------------------------------


def test_list_trades_empty(client: TestClient) -> None:
    resp = client.get("/api/trades")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_trades_excludes_cancelled(client: TestClient, db: Session) -> None:
    make_trade(db, status="open")
    make_trade(db, status="cancelled")
    resp = client.get("/api/trades")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_trades_with_strategy_filter(client: TestClient, db: Session) -> None:
    make_trade(db, strategy="strat-a")
    make_trade(db, strategy="strat-b")
    resp = client.get("/api/trades", params={"strategy": "strat-a"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["strategy"] == "strat-a"


def test_list_trades_respects_limit(client: TestClient, db: Session) -> None:
    for _ in range(5):
        make_trade(db)
    resp = client.get("/api/trades", params={"limit": 2})
    assert len(resp.json()) == 2


# ---------------------------------------------------------------------------
# GET /api/trades/{id}
# ---------------------------------------------------------------------------


def test_get_trade_found(client: TestClient, db: Session) -> None:
    trade = make_trade(db)
    resp = client.get(f"/api/trades/{trade.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == trade.id


def test_get_trade_not_found(client: TestClient) -> None:
    resp = client.get("/api/trades/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PUT /api/trades/{id}
# ---------------------------------------------------------------------------


def test_update_trade_notes(client: TestClient, db: Session) -> None:
    trade = make_trade(db)
    resp = client.put(
        f"/api/trades/{trade.id}",
        json={"notes": "Good setup"},
    )
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Good setup"


def test_close_trade_auto_calculates_pnl(client: TestClient, db: Session) -> None:
    trade = make_trade(db, entry_price=1.08000, sl_price=1.07700, risk_pips=30.0)
    resp = client.put(
        f"/api/trades/{trade.id}",
        json={
            "exit_price": 1.08300,
            "status": "closed",
            "outcome": "win",
            "close_time": "2025-03-02T14:00:00Z",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pnl_pips"] == 30.0
    assert data["pnl_usd"] is not None
    assert data["rr_achieved"] == 1.0


def test_update_trade_not_found(client: TestClient) -> None:
    resp = client.put("/api/trades/nonexistent", json={"notes": "x"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/trades/{id}
# ---------------------------------------------------------------------------


def test_delete_trade_returns_204(client: TestClient, db: Session) -> None:
    trade = make_trade(db)
    resp = client.delete(f"/api/trades/{trade.id}")
    assert resp.status_code == 204
    assert client.get(f"/api/trades/{trade.id}").status_code == 404


def test_delete_trade_not_found(client: TestClient) -> None:
    resp = client.delete("/api/trades/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/trades/stats
# ---------------------------------------------------------------------------


def test_stats_empty_returns_zeros(client: TestClient) -> None:
    resp = client.get("/api/trades/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_trades"] == 0
    assert data["wins"] == 0


def test_stats_reflects_closed_trades(client: TestClient, db: Session) -> None:
    base = datetime(2025, 3, 1, 10, 0, tzinfo=timezone.utc)
    make_trade(
        db, status="closed", outcome="win",
        pnl_pips=20.0, pnl_usd=100.0, rr_achieved=2.0,
        open_time=base, close_time=base,
    )
    make_trade(
        db, status="closed", outcome="loss",
        pnl_pips=-10.0, pnl_usd=-50.0, rr_achieved=-1.0,
        open_time=base, close_time=base,
    )
    resp = client.get("/api/trades/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["wins"] == 1
    assert data["losses"] == 1
    assert data["total_pnl_pips"] == 10.0
