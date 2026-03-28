"""
tests/test_accounts_api.py
---------------------------
Integration tests for /api/accounts endpoints.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models import AccountModel
from tests.conftest import make_trade


def _account_payload(**overrides: object) -> dict:
    """Return a valid AccountCreateRequest body with optional overrides."""
    base: dict = {
        "name": "My Demo",
        "account_type": "demo",
        "instrument_type": "forex",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# POST /api/accounts
# ---------------------------------------------------------------------------


def test_create_account_returns_201(client: TestClient) -> None:
    resp = client.post("/api/accounts", json=_account_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "My Demo"
    assert data["account_type"] == "demo"
    assert data["instrument_type"] == "forex"
    assert data["status"] == "active"


def test_create_account_invalid_type_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/accounts", json=_account_payload(account_type="invalid"),
    )
    assert resp.status_code == 422


def test_create_account_invalid_instrument_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/accounts", json=_account_payload(instrument_type="crypto"),
    )
    assert resp.status_code == 422


def test_create_funded_account_with_details(client: TestClient) -> None:
    resp = client.post("/api/accounts", json=_account_payload(
        account_type="funded",
        prop_firm="FTMO",
        phase="Phase 1",
    ))
    assert resp.status_code == 201
    data = resp.json()
    assert data["prop_firm"] == "FTMO"
    assert data["phase"] == "Phase 1"


# ---------------------------------------------------------------------------
# GET /api/accounts
# ---------------------------------------------------------------------------


def test_list_accounts_empty(client: TestClient) -> None:
    resp = client.get("/api/accounts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_accounts_returns_created(client: TestClient) -> None:
    client.post("/api/accounts", json=_account_payload(name="A"))
    client.post("/api/accounts", json=_account_payload(name="B"))
    resp = client.get("/api/accounts")
    assert len(resp.json()) == 2


def test_list_accounts_filter_by_instrument(client: TestClient) -> None:
    client.post("/api/accounts", json=_account_payload(instrument_type="forex"))
    client.post(
        "/api/accounts",
        json=_account_payload(instrument_type="futures_mnq"),
    )
    resp = client.get("/api/accounts", params={"instrument_type": "futures_mnq"})
    data = resp.json()
    assert len(data) == 1
    assert data[0]["instrument_type"] == "futures_mnq"


# ---------------------------------------------------------------------------
# PUT /api/accounts/{id}
# ---------------------------------------------------------------------------


def test_update_account_name(client: TestClient) -> None:
    create_resp = client.post("/api/accounts", json=_account_payload())
    account_id = create_resp.json()["id"]
    resp = client.put(f"/api/accounts/{account_id}", json={"name": "Renamed"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


def test_update_account_not_found(client: TestClient) -> None:
    resp = client.put("/api/accounts/nonexistent", json={"name": "X"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/accounts/{id}
# ---------------------------------------------------------------------------


def test_delete_account_returns_204(client: TestClient) -> None:
    create_resp = client.post("/api/accounts", json=_account_payload())
    account_id = create_resp.json()["id"]
    resp = client.delete(f"/api/accounts/{account_id}")
    assert resp.status_code == 204


def test_delete_account_not_found(client: TestClient) -> None:
    resp = client.delete("/api/accounts/nonexistent")
    assert resp.status_code == 404


def test_delete_account_with_linked_trades_returns_409(
    client: TestClient, db: Session, sample_account: AccountModel,
) -> None:
    make_trade(db, account_id=sample_account.id)
    resp = client.delete(f"/api/accounts/{sample_account.id}")
    assert resp.status_code == 409
