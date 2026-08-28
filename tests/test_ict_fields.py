"""
tests/test_ict_fields.py
------------------------
Integration tests for ICT trade fields on the /api/trades endpoints.

Covers: creation with ICT fields, cross-field validator (ict_setup_detail vs
ict_setup_type), PUT updates for ICT fields, and None defaults.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from shared.ict_taxonomy import (
    CONTINUATION_DETAILS,
    IFVG_TIMEFRAMES,
    LIQUIDITY_SWEEP_DETAILS,
    TP_TARGET_DETAIL_MAP,
    TP_TARGETS,
    UNMITIGATED_FVG_DETAILS,
)
from tests.conftest import make_trade

OPEN_TIME = "2025-03-01T12:00:00Z"


def _base_payload(**overrides: object) -> dict:
    """Return a minimal valid TradeCreateRequest body with optional overrides."""
    base: dict = {
        "strategy": "ict-mnq",
        "symbol": "MNQ",
        "instrument_type": "futures_mnq",
        "direction": "BUY",
        "entry_price": 21000.0,
        "sl_price": 20950.0,
        "lot_size": 1.0,
        "risk_pips": 50.0,
        "open_time": OPEN_TIME,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# ICT fields present in POST response
# ---------------------------------------------------------------------------


def test_create_trade_with_ict_fields_returns_201(client: TestClient) -> None:
    """All ICT fields round-trip correctly through POST /api/trades."""
    payload = _base_payload(
        ict_setup_type="liquidity_sweep",
        ict_setup_detail=LIQUIDITY_SWEEP_DETAILS[0],
        ict_tp_target=TP_TARGETS[0],
        ict_ifvg_timeframe=IFVG_TIMEFRAMES[0],
        ict_smt_present=True,
        ict_tdo_aligned=False,
        ict_cisd_present=True,
    )
    resp = client.post("/api/trades", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["ict_setup_type"] == "liquidity_sweep"
    assert data["ict_setup_detail"] == LIQUIDITY_SWEEP_DETAILS[0]
    assert data["ict_tp_target"] == TP_TARGETS[0]
    assert data["ict_ifvg_timeframe"] == IFVG_TIMEFRAMES[0]
    assert data["ict_smt_present"] is True
    assert data["ict_tdo_aligned"] is False
    assert data["ict_cisd_present"] is True


def test_create_trade_ict_fields_default_to_none(client: TestClient) -> None:
    """ICT fields are None when omitted from the request."""
    resp = client.post("/api/trades", json=_base_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["ict_setup_type"] is None
    assert data["ict_setup_detail"] is None
    assert data["ict_tp_target"] is None
    assert data["ict_ifvg_timeframe"] is None
    assert data["ict_smt_present"] is None
    assert data["ict_tdo_aligned"] is None
    assert data["ict_cisd_present"] is None


# ---------------------------------------------------------------------------
# Cross-field validator: ict_setup_detail must match ict_setup_type
# ---------------------------------------------------------------------------


def test_create_trade_ict_detail_wrong_for_type_returns_422(
    client: TestClient,
) -> None:
    """A detail from UNMITIGATED_FVG_DETAILS is invalid for liquidity_sweep."""
    payload = _base_payload(
        ict_setup_type="liquidity_sweep",
        ict_setup_detail=UNMITIGATED_FVG_DETAILS[0],
    )
    resp = client.post("/api/trades", json=payload)
    assert resp.status_code == 422


def test_create_trade_ict_detail_wrong_for_continuation_returns_422(
    client: TestClient,
) -> None:
    """A detail from LIQUIDITY_SWEEP_DETAILS is invalid for continuation."""
    payload = _base_payload(
        ict_setup_type="continuation",
        ict_setup_detail=LIQUIDITY_SWEEP_DETAILS[0],
    )
    resp = client.post("/api/trades", json=payload)
    assert resp.status_code == 422


def test_create_trade_ict_detail_valid_for_unmitigated_fvg_passes(
    client: TestClient,
) -> None:
    """A detail from UNMITIGATED_FVG_DETAILS is valid for unmitigated_fvg."""
    payload = _base_payload(
        ict_setup_type="unmitigated_fvg",
        ict_setup_detail=UNMITIGATED_FVG_DETAILS[0],
    )
    resp = client.post("/api/trades", json=payload)
    assert resp.status_code == 201
    assert resp.json()["ict_setup_detail"] == UNMITIGATED_FVG_DETAILS[0]


def test_create_trade_ict_detail_valid_for_continuation_passes(
    client: TestClient,
) -> None:
    """A detail from CONTINUATION_DETAILS is valid for continuation."""
    payload = _base_payload(
        ict_setup_type="continuation",
        ict_setup_detail=CONTINUATION_DETAILS[0],
    )
    resp = client.post("/api/trades", json=payload)
    assert resp.status_code == 201
    assert resp.json()["ict_setup_detail"] == CONTINUATION_DETAILS[0]


def test_create_trade_ict_setup_type_other_accepts_no_detail(
    client: TestClient,
) -> None:
    """setup_type='other' has no allowed details; passing detail 'other' is still a raw value."""
    payload = _base_payload(ict_setup_type="other")
    resp = client.post("/api/trades", json=payload)
    assert resp.status_code == 201
    assert resp.json()["ict_setup_type"] == "other"


def test_create_trade_invalid_ict_setup_type_returns_422(
    client: TestClient,
) -> None:
    """An unrecognised ict_setup_type string must be rejected with 422."""
    resp = client.post(
        "/api/trades", json=_base_payload(ict_setup_type="invalid_type"),
    )
    assert resp.status_code == 422


def test_create_trade_invalid_ict_tp_target_returns_422(
    client: TestClient,
) -> None:
    """An unrecognised ict_tp_target string must be rejected with 422."""
    resp = client.post(
        "/api/trades", json=_base_payload(ict_tp_target="bad_target"),
    )
    assert resp.status_code == 422


def test_create_trade_invalid_ict_ifvg_timeframe_returns_422(
    client: TestClient,
) -> None:
    """An unrecognised ict_ifvg_timeframe string must be rejected with 422."""
    resp = client.post(
        "/api/trades", json=_base_payload(ict_ifvg_timeframe="999m"),
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/trades/{id} — ICT fields update
# ---------------------------------------------------------------------------


def test_update_trade_ict_fields_via_put(
    client: TestClient, db: Session,
) -> None:
    """PUT /api/trades/{id} correctly stores and returns updated ICT fields."""
    trade = make_trade(db, instrument_type="futures_mnq")
    resp = client.put(
        f"/api/trades/{trade.id}",
        json={
            "ict_setup_type": "unmitigated_fvg",
            "ict_setup_detail": UNMITIGATED_FVG_DETAILS[1],
            "ict_tp_target": TP_TARGETS[1],
            "ict_ifvg_timeframe": IFVG_TIMEFRAMES[2],
            "ict_smt_present": False,
            "ict_tdo_aligned": True,
            "ict_cisd_present": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ict_setup_type"] == "unmitigated_fvg"
    assert data["ict_setup_detail"] == UNMITIGATED_FVG_DETAILS[1]
    assert data["ict_tp_target"] == TP_TARGETS[1]
    assert data["ict_ifvg_timeframe"] == IFVG_TIMEFRAMES[2]
    assert data["ict_smt_present"] is False
    assert data["ict_tdo_aligned"] is True
    assert data["ict_cisd_present"] is True


def test_update_trade_ict_detail_wrong_for_type_returns_422(
    client: TestClient, db: Session,
) -> None:
    """Cross-field validator fires on PUT when detail does not match type."""
    trade = make_trade(db, instrument_type="futures_mnq")
    resp = client.put(
        f"/api/trades/{trade.id}",
        json={
            "ict_setup_type": "continuation",
            "ict_setup_detail": LIQUIDITY_SWEEP_DETAILS[0],
        },
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Cross-field validator: ict_tp_target_detail must match ict_tp_target
# ---------------------------------------------------------------------------


def test_create_trade_tp_target_detail_valid_for_ith_passes(
    client: TestClient,
) -> None:
    """A detail from TP_TARGET_DETAIL_MAP['ith'] is valid for tp_target='ith'."""
    payload = _base_payload(
        ict_tp_target="ith",
        ict_tp_target_detail=TP_TARGET_DETAIL_MAP["ith"][0],
    )
    resp = client.post("/api/trades", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["ict_tp_target"] == "ith"
    assert data["ict_tp_target_detail"] == TP_TARGET_DETAIL_MAP["ith"][0]


def test_create_trade_tp_target_detail_wrong_for_target_returns_422(
    client: TestClient,
) -> None:
    """A detail valid only for unmitigated_fvg (e.g. '2h') is invalid for tp_target='ith'."""
    payload = _base_payload(ict_tp_target="ith", ict_tp_target_detail="2h")
    resp = client.post("/api/trades", json=payload)
    assert resp.status_code == 422


def test_create_trade_tp_target_detail_valid_for_unmitigated_fvg_monthly_passes(
    client: TestClient,
) -> None:
    """The newly added monthly FVG timeframe ('1M') is valid for unmitigated_fvg."""
    payload = _base_payload(ict_tp_target="unmitigated_fvg", ict_tp_target_detail="1M")
    resp = client.post("/api/trades", json=payload)
    assert resp.status_code == 201
    assert resp.json()["ict_tp_target_detail"] == "1M"


def test_create_trade_tp_target_detail_valid_for_data_release_passes(
    client: TestClient,
) -> None:
    """A release-type detail is valid for tp_target='data_release_high'."""
    payload = _base_payload(ict_tp_target="data_release_high", ict_tp_target_detail="cpi")
    resp = client.post("/api/trades", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["ict_tp_target"] == "data_release_high"
    assert data["ict_tp_target_detail"] == "cpi"


def test_create_trade_invalid_tp_target_detail_returns_422(
    client: TestClient,
) -> None:
    """An unrecognised ict_tp_target_detail string must be rejected with 422."""
    resp = client.post(
        "/api/trades",
        json=_base_payload(ict_tp_target="ith", ict_tp_target_detail="bad_detail"),
    )
    assert resp.status_code == 422


def test_update_trade_tp_target_detail_wrong_for_target_returns_422(
    client: TestClient, db: Session,
) -> None:
    """Cross-field validator fires on PUT when tp_target_detail does not match tp_target."""
    trade = make_trade(db, instrument_type="futures_mnq")
    resp = client.put(
        f"/api/trades/{trade.id}",
        json={"ict_tp_target": "itl", "ict_tp_target_detail": "1M"},
    )
    assert resp.status_code == 422
