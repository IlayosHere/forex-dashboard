"""
tests/test_qt_taxonomy.py
-------------------------
Unit tests for shared/qt_taxonomy.py constants and the qt_* field
validators on TradeCreateRequest / TradeUpdateRequest in api/schemas_trade.py.
API-level round-trips use the real in-memory SQLite client from conftest.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.schemas_trade import TradeCreateRequest, TradeUpdateRequest
from shared.qt_taxonomy import (
    QT_ENTRY_TYPES,
    QT_FVG_TYPES,
    QT_QUARTERS,
    QT_TP_TARGETS,
)


# ---------------------------------------------------------------------------
# 1. Constants — structural shape
# ---------------------------------------------------------------------------


def test_qt_quarters_contains_16_values() -> None:
    """QT_QUARTERS must enumerate all 4 sessions × 4 quarters."""
    assert len(QT_QUARTERS) == 16


def test_qt_quarters_sessions_all_present() -> None:
    sessions = {"asia", "london", "ny_am", "ny_pm"}
    found = {v.rsplit("_q", 1)[0] for v in QT_QUARTERS}
    assert found == sessions


def test_qt_quarters_quarter_numbers_1_to_4() -> None:
    suffixes = {v.rsplit("_q", 1)[1] for v in QT_QUARTERS}
    assert suffixes == {"1", "2", "3", "4"}


def test_qt_fvg_types_contains_standard_and_inverse() -> None:
    assert set(QT_FVG_TYPES) == {"standard", "inverse"}


def test_qt_entry_types_contains_expected_values() -> None:
    assert set(QT_ENTRY_TYPES) == {"limit_fvg_edge", "market_mss"}


def test_qt_tp_targets_contains_11_values() -> None:
    assert len(QT_TP_TARGETS) == 11


def test_qt_tp_targets_contains_other() -> None:
    assert "other" in QT_TP_TARGETS


# ---------------------------------------------------------------------------
# 2. TradeCreateRequest — qt_fvg_quarter validator
# ---------------------------------------------------------------------------

_BASE_TRADE: dict = {
    "strategy": "qt-mnq",
    "symbol": "MNQ",
    "direction": "BUY",
    "entry_price": 19500.0,
    "sl_price": 19480.0,
    "lot_size": 1.0,
    "risk_pips": 20.0,
    "open_time": "2025-03-10T09:00:00Z",
    "instrument_type": "futures_mnq",
}


def test_create_request_qt_fvg_quarter_valid() -> None:
    req = TradeCreateRequest(**{**_BASE_TRADE, "qt_fvg_quarter": "ny_am_q1"})
    assert req.qt_fvg_quarter == "ny_am_q1"


def test_create_request_qt_fvg_quarter_none_accepted() -> None:
    req = TradeCreateRequest(**{**_BASE_TRADE, "qt_fvg_quarter": None})
    assert req.qt_fvg_quarter is None


def test_create_request_qt_fvg_quarter_invalid_raises() -> None:
    with pytest.raises(ValidationError, match="qt_fvg_quarter"):
        TradeCreateRequest(**{**_BASE_TRADE, "qt_fvg_quarter": "tokyo_q1"})


# ---------------------------------------------------------------------------
# 3. TradeCreateRequest — qt_entry_quarter validator
# ---------------------------------------------------------------------------


def test_create_request_qt_entry_quarter_valid() -> None:
    req = TradeCreateRequest(**{**_BASE_TRADE, "qt_entry_quarter": "london_q3"})
    assert req.qt_entry_quarter == "london_q3"


def test_create_request_qt_entry_quarter_invalid_raises() -> None:
    with pytest.raises(ValidationError, match="qt_entry_quarter"):
        TradeCreateRequest(**{**_BASE_TRADE, "qt_entry_quarter": "bad_value"})


# ---------------------------------------------------------------------------
# 4. TradeCreateRequest — qt_fvg_type validator
# ---------------------------------------------------------------------------


def test_create_request_qt_fvg_type_standard_accepted() -> None:
    req = TradeCreateRequest(**{**_BASE_TRADE, "qt_fvg_type": "standard"})
    assert req.qt_fvg_type == "standard"


def test_create_request_qt_fvg_type_inverse_accepted() -> None:
    req = TradeCreateRequest(**{**_BASE_TRADE, "qt_fvg_type": "inverse"})
    assert req.qt_fvg_type == "inverse"


def test_create_request_qt_fvg_type_invalid_raises() -> None:
    with pytest.raises(ValidationError, match="qt_fvg_type"):
        TradeCreateRequest(**{**_BASE_TRADE, "qt_fvg_type": "extended"})


# ---------------------------------------------------------------------------
# 5. TradeCreateRequest — qt_entry_type validator
# ---------------------------------------------------------------------------


def test_create_request_qt_entry_type_limit_accepted() -> None:
    req = TradeCreateRequest(**{**_BASE_TRADE, "qt_entry_type": "limit_fvg_edge"})
    assert req.qt_entry_type == "limit_fvg_edge"


def test_create_request_qt_entry_type_market_accepted() -> None:
    req = TradeCreateRequest(**{**_BASE_TRADE, "qt_entry_type": "market_mss"})
    assert req.qt_entry_type == "market_mss"


def test_create_request_qt_entry_type_invalid_raises() -> None:
    with pytest.raises(ValidationError, match="qt_entry_type"):
        TradeCreateRequest(**{**_BASE_TRADE, "qt_entry_type": "stop_order"})


# ---------------------------------------------------------------------------
# 6. TradeUpdateRequest — all four qt_* validators
# ---------------------------------------------------------------------------


def test_update_request_qt_fvg_quarter_valid() -> None:
    req = TradeUpdateRequest(qt_fvg_quarter="asia_q2")
    assert req.qt_fvg_quarter == "asia_q2"


def test_update_request_qt_fvg_quarter_invalid_raises() -> None:
    with pytest.raises(ValidationError, match="qt_fvg_quarter"):
        TradeUpdateRequest(qt_fvg_quarter="session_q9")


def test_update_request_qt_entry_quarter_valid() -> None:
    req = TradeUpdateRequest(qt_entry_quarter="ny_pm_q4")
    assert req.qt_entry_quarter == "ny_pm_q4"


def test_update_request_qt_entry_quarter_invalid_raises() -> None:
    with pytest.raises(ValidationError, match="qt_entry_quarter"):
        TradeUpdateRequest(qt_entry_quarter="invalid")


def test_update_request_qt_fvg_type_valid() -> None:
    req = TradeUpdateRequest(qt_fvg_type="inverse")
    assert req.qt_fvg_type == "inverse"


def test_update_request_qt_fvg_type_invalid_raises() -> None:
    with pytest.raises(ValidationError, match="qt_fvg_type"):
        TradeUpdateRequest(qt_fvg_type="partial")


def test_update_request_qt_entry_type_valid() -> None:
    req = TradeUpdateRequest(qt_entry_type="market_mss")
    assert req.qt_entry_type == "market_mss"


def test_update_request_qt_entry_type_invalid_raises() -> None:
    with pytest.raises(ValidationError, match="qt_entry_type"):
        TradeUpdateRequest(qt_entry_type="breakout")


# ---------------------------------------------------------------------------
# 7. API round-trip — QT fields persisted and returned
# ---------------------------------------------------------------------------


def _qt_trade_payload(**overrides: object) -> dict:
    """Base payload for a QT trade with all four qt_* fields set."""
    base: dict = {
        "strategy": "qt-mnq",
        "symbol": "MNQ",
        "direction": "BUY",
        "entry_price": 19500.0,
        "sl_price": 19480.0,
        "lot_size": 1.0,
        "risk_pips": 20.0,
        "open_time": "2025-03-10T09:00:00Z",
        "instrument_type": "futures_mnq",
        "qt_fvg_quarter": "ny_am_q1",
        "qt_entry_quarter": "ny_am_q2",
        "qt_fvg_type": "standard",
        "qt_entry_type": "limit_fvg_edge",
    }
    base.update(overrides)
    return base


def test_create_trade_qt_fields_persisted(client: TestClient) -> None:
    resp = client.post("/api/trades", json=_qt_trade_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["qt_fvg_quarter"] == "ny_am_q1"
    assert data["qt_entry_quarter"] == "ny_am_q2"
    assert data["qt_fvg_type"] == "standard"
    assert data["qt_entry_type"] == "limit_fvg_edge"


def test_create_trade_qt_fields_null_by_default(client: TestClient) -> None:
    resp = client.post(
        "/api/trades",
        json={
            "strategy": "fvg-impulse",
            "symbol": "EURUSD",
            "direction": "BUY",
            "entry_price": 1.085,
            "sl_price": 1.082,
            "lot_size": 0.5,
            "risk_pips": 30.0,
            "open_time": "2025-03-01T12:00:00Z",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["qt_fvg_quarter"] is None
    assert data["qt_entry_quarter"] is None
    assert data["qt_fvg_type"] is None
    assert data["qt_entry_type"] is None


def test_create_trade_invalid_qt_fvg_quarter_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/trades", json=_qt_trade_payload(qt_fvg_quarter="bad_quarter"),
    )
    assert resp.status_code == 422


def test_create_trade_invalid_qt_fvg_type_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/trades", json=_qt_trade_payload(qt_fvg_type="unknown"),
    )
    assert resp.status_code == 422


def test_update_trade_qt_fields(client: TestClient) -> None:
    create_resp = client.post("/api/trades", json=_qt_trade_payload())
    assert create_resp.status_code == 201
    trade_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/api/trades/{trade_id}",
        json={"qt_fvg_quarter": "london_q2", "qt_fvg_type": "inverse"},
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["qt_fvg_quarter"] == "london_q2"
    assert data["qt_fvg_type"] == "inverse"


def test_update_trade_invalid_qt_entry_type_returns_422(client: TestClient) -> None:
    create_resp = client.post("/api/trades", json=_qt_trade_payload())
    assert create_resp.status_code == 201
    trade_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/api/trades/{trade_id}", json={"qt_entry_type": "not_valid"},
    )
    assert update_resp.status_code == 422
