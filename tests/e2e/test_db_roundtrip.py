"""
tests/e2e/test_db_roundtrip.py
------------------------------
Full CRUD round-trip against /api/trades, which proves the api
Cloud Run service can reach Cloud SQL and that the full read/write
path works end-to-end.

Trade payload shape is built from api/schemas_trade.py:TradeCreateRequest.
Required fields: strategy, symbol, direction, entry_price, sl_price,
lot_size, open_time. A unique e2e marker on strategy + symbol prevents
collisions with real trade data.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

E2E_STRATEGY = "e2e-test"
E2E_SYMBOL = "E2EUSD"


def _build_trade_payload() -> dict:
    """Minimal valid payload matching TradeCreateRequest."""
    return {
        "strategy": E2E_STRATEGY,
        "symbol": E2E_SYMBOL,
        "direction": "BUY",
        "entry_price": 1.1000,
        "sl_price": 1.0950,
        "tp_price": 1.1100,
        "lot_size": 0.10,
        "risk_pips": 50.0,
        "open_time": datetime.now(timezone.utc).isoformat(),
        "tags": ["e2e"],
        "notes": "e2e round-trip test",
    }


def test_create_get_update_delete_trade(
    api_url: str,
    auth_headers: dict[str, str],
    client: httpx.Client,
) -> None:
    """Create -> Read -> Close (compute P&L) -> Delete -> 404."""
    base = f"{api_url}/api/trades"
    payload = _build_trade_payload()

    # ---- CREATE --------------------------------------------------------
    create_resp = client.post(base, headers=auth_headers, json=payload)
    assert create_resp.status_code in (200, 201), (
        f"POST /api/trades returned {create_resp.status_code}: "
        f"{create_resp.text}"
    )
    created = create_resp.json()
    trade_id = created.get("id")
    assert trade_id, f"created trade missing id: {created}"
    assert created["strategy"] == E2E_STRATEGY
    assert created["symbol"] == E2E_SYMBOL

    try:
        # ---- READ ------------------------------------------------------
        get_resp = client.get(f"{base}/{trade_id}", headers=auth_headers)
        assert get_resp.status_code == 200, (
            f"GET /api/trades/{trade_id} returned {get_resp.status_code}: "
            f"{get_resp.text}"
        )
        fetched = get_resp.json()
        assert fetched["id"] == trade_id
        assert fetched["strategy"] == E2E_STRATEGY
        assert fetched["symbol"] == E2E_SYMBOL
        assert fetched["entry_price"] == payload["entry_price"]

        # ---- UPDATE (close with exit price) ---------------------------
        close_body = {
            "status": "closed",
            "outcome": "win",
            "exit_price": 1.1100,
            "close_time": datetime.now(timezone.utc).isoformat(),
        }
        put_resp = client.put(
            f"{base}/{trade_id}", headers=auth_headers, json=close_body,
        )
        assert put_resp.status_code == 200, (
            f"PUT /api/trades/{trade_id} returned {put_resp.status_code}: "
            f"{put_resp.text}"
        )
        closed = put_resp.json()
        assert closed["status"] == "closed"
        assert closed["exit_price"] == 1.1100
        # P&L should have been computed server-side on close.
        assert closed.get("pnl_usd") is not None, (
            f"pnl_usd was not computed on close: {closed}"
        )
    finally:
        # ---- DELETE ----------------------------------------------------
        del_resp = client.delete(f"{base}/{trade_id}", headers=auth_headers)
        assert del_resp.status_code == 204, (
            f"DELETE /api/trades/{trade_id} returned {del_resp.status_code}: "
            f"{del_resp.text}"
        )

    # ---- VERIFY GONE ---------------------------------------------------
    gone_resp = client.get(f"{base}/{trade_id}", headers=auth_headers)
    assert gone_resp.status_code == 404, (
        f"GET after DELETE should 404; got {gone_resp.status_code}: "
        f"{gone_resp.text}"
    )
