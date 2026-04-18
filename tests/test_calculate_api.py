"""
tests/test_calculate_api.py
----------------------------
Integration tests for POST /api/calculate.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

CALCULATE_URL = "/api/calculate"

VALID_FOREX_PAYLOAD: dict = {
    "symbol": "EURUSD",
    "entry": 1.08500,
    "sl_pips": 20.0,
    "account_balance": 10000.0,
    "risk_percent": 1.0,
}


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_calculate_valid_request_returns_200(client: TestClient) -> None:
    """Valid forex payload returns 200 with all required response fields."""
    resp = client.post(CALCULATE_URL, json=VALID_FOREX_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    assert "lot_size" in data
    assert "risk_usd" in data
    assert "sl_pips" in data
    assert "rr" in data


def test_calculate_lot_size_value(client: TestClient) -> None:
    """Lot size for 1% of $10,000 at 20 pips SL on EURUSD is correct."""
    resp = client.post(CALCULATE_URL, json=VALID_FOREX_PAYLOAD)
    assert resp.status_code == 200
    data = resp.json()
    # risk_usd = 10000 * 0.01 = 100, pip_value = 10 (USD quote pair)
    # raw_lots = 100 / (20 * 10) = 0.5
    assert data["lot_size"] == 0.5
    assert data["risk_usd"] == 100.0
    assert data["sl_pips"] == 20.0


def test_calculate_with_tp_returns_rr(client: TestClient) -> None:
    """When tp_pips is provided, rr is calculated."""
    payload = {**VALID_FOREX_PAYLOAD, "tp_pips": 40.0}
    resp = client.post(CALCULATE_URL, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["rr"] == 2.0


def test_calculate_without_tp_rr_is_none(client: TestClient) -> None:
    """When tp_pips is omitted, rr is None."""
    resp = client.post(CALCULATE_URL, json=VALID_FOREX_PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["rr"] is None


def test_calculate_futures_mnq_instrument(client: TestClient) -> None:
    """futures_mnq instrument_type uses point-based contract calculation."""
    payload = {
        "symbol": "MNQ",
        "entry": 19000.0,
        "sl_pips": 50.0,
        "account_balance": 5000.0,
        "risk_percent": 2.0,
        "instrument_type": "futures_mnq",
    }
    resp = client.post(CALCULATE_URL, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["instrument_type"] == "futures_mnq"
    # lot_size represents contracts; minimum is 1
    assert data["lot_size"] >= 1


def test_calculate_min_lot_floor_applied(client: TestClient) -> None:
    """Very small risk results in the minimum 0.01 lot size being applied."""
    payload = {
        "symbol": "EURUSD",
        "entry": 1.08500,
        "sl_pips": 100.0,
        "account_balance": 100.0,
        "risk_percent": 0.1,
    }
    resp = client.post(CALCULATE_URL, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # risk_usd = 0.10, pip_value = 10 → raw = 0.001 → floored to 0.01
    assert data["lot_size"] == 0.01
    assert data["min_lot_applied"] is True


def test_calculate_instrument_type_echoed_back(client: TestClient) -> None:
    """instrument_type is echoed back in the response."""
    resp = client.post(CALCULATE_URL, json=VALID_FOREX_PAYLOAD)
    assert resp.status_code == 200
    assert resp.json()["instrument_type"] == "forex"


# ---------------------------------------------------------------------------
# Zero / negative SL distance
# ---------------------------------------------------------------------------


def test_calculate_zero_sl_returns_minimum_lot(client: TestClient) -> None:
    """sl_pips of zero is rejected by Pydantic (gt=0) with 422."""
    payload = {**VALID_FOREX_PAYLOAD, "sl_pips": 0}
    resp = client.post(CALCULATE_URL, json=payload)
    assert resp.status_code == 422


def test_calculate_negative_sl_returns_422(client: TestClient) -> None:
    """Negative sl_pips is rejected by Pydantic with 422."""
    payload = {**VALID_FOREX_PAYLOAD, "sl_pips": -5.0}
    resp = client.post(CALCULATE_URL, json=payload)
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def test_calculate_requires_auth(raw_client: TestClient) -> None:
    """Request without a Bearer token returns 401."""
    resp = raw_client.post(CALCULATE_URL, json=VALID_FOREX_PAYLOAD)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Validation errors (422)
# ---------------------------------------------------------------------------


def test_calculate_missing_symbol_returns_422(client: TestClient) -> None:
    """Missing required 'symbol' field returns 422."""
    payload = {k: v for k, v in VALID_FOREX_PAYLOAD.items() if k != "symbol"}
    resp = client.post(CALCULATE_URL, json=payload)
    assert resp.status_code == 422


def test_calculate_missing_entry_returns_422(client: TestClient) -> None:
    """Missing required 'entry' field returns 422."""
    payload = {k: v for k, v in VALID_FOREX_PAYLOAD.items() if k != "entry"}
    resp = client.post(CALCULATE_URL, json=payload)
    assert resp.status_code == 422


def test_calculate_missing_sl_pips_returns_422(client: TestClient) -> None:
    """Missing required 'sl_pips' field returns 422."""
    payload = {k: v for k, v in VALID_FOREX_PAYLOAD.items() if k != "sl_pips"}
    resp = client.post(CALCULATE_URL, json=payload)
    assert resp.status_code == 422


def test_calculate_empty_body_returns_422(client: TestClient) -> None:
    """Empty body returns 422."""
    resp = client.post(CALCULATE_URL, json={})
    assert resp.status_code == 422
