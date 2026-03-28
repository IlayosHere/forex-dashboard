"""
tests/test_signals_api.py
--------------------------
Integration tests for /api/signals endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models import SignalModel


def _insert_signal(db: Session, **overrides: object) -> SignalModel:
    """Insert a signal with sensible defaults and optional overrides."""
    defaults: dict = {
        "id": str(uuid.uuid4()),
        "strategy": "fvg-impulse",
        "symbol": "EURUSD",
        "direction": "BUY",
        "candle_time": datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc),
        "entry": 1.08500,
        "sl": 1.08200,
        "tp": 1.09100,
        "lot_size": 0.50,
        "risk_pips": 30.0,
        "spread_pips": 1.2,
        "signal_metadata": {"fvg_size": 15},
        "created_at": datetime.now(timezone.utc),
    }
    defaults.update(overrides)
    signal = SignalModel(**defaults)
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return signal


# ---------------------------------------------------------------------------
# GET /api/signals
# ---------------------------------------------------------------------------


def test_list_signals_empty(client: TestClient) -> None:
    resp = client.get("/api/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


def test_list_signals_returns_items(client: TestClient, db: Session) -> None:
    _insert_signal(db)
    _insert_signal(db)
    resp = client.get("/api/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_list_signals_filter_by_strategy(client: TestClient, db: Session) -> None:
    _insert_signal(db, strategy="fvg-impulse")
    _insert_signal(db, strategy="other-strat")
    resp = client.get("/api/signals", params={"strategy": "fvg-impulse"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["strategy"] == "fvg-impulse"


def test_list_signals_filter_by_symbol(client: TestClient, db: Session) -> None:
    _insert_signal(db, symbol="EURUSD")
    _insert_signal(db, symbol="GBPUSD")
    resp = client.get("/api/signals", params={"symbol": "GBPUSD"})
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["symbol"] == "GBPUSD"


def test_list_signals_respects_limit(client: TestClient, db: Session) -> None:
    for _ in range(5):
        _insert_signal(db)
    resp = client.get("/api/signals", params={"limit": 2})
    data = resp.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2


def test_list_signals_pagination_offset(client: TestClient, db: Session) -> None:
    for _ in range(5):
        _insert_signal(db)
    resp = client.get("/api/signals", params={"limit": 2, "offset": 4})
    data = resp.json()
    assert len(data["items"]) == 1


# ---------------------------------------------------------------------------
# GET /api/signals/{id}
# ---------------------------------------------------------------------------


def test_get_signal_found(client: TestClient, db: Session) -> None:
    signal = _insert_signal(db)
    resp = client.get(f"/api/signals/{signal.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == signal.id
    assert data["strategy"] == "fvg-impulse"
    assert data["metadata"] == {"fvg_size": 15}


def test_get_signal_not_found(client: TestClient) -> None:
    resp = client.get("/api/signals/nonexistent")
    assert resp.status_code == 404
