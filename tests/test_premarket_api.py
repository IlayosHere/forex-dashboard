"""
tests/test_premarket_api.py
----------------------------
Integration tests for the pre-market routine endpoints: plan upsert, scenarios
(create/get/update/delete), checkpoints, review, and the date-range summary list.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models_premarket import PlanScenarioModel, PremarketPlanModel
from tests.conftest import TEST_USER


def _make_plan_with_scenario(db: Session, *, owner: str = TEST_USER, date_: str = "2026-05-11") -> str:
    """Insert a plan + one scenario directly via the DB, bypassing the API/owner-override.

    Mirrors the pattern in test_user_isolation.py: seed the "victim" user's data with a
    raw DB session so the test only needs a single TestClient fixture — combining `client`
    and `client_other_user` in one test is unsafe, since dependency_overrides lives on the
    shared `app` object and the second fixture's override wins for both clients.
    """
    now = datetime.now(timezone.utc)
    plan = PremarketPlanModel(
        id=str(uuid.uuid4()), owner=owner, date=datetime.strptime(date_, "%Y-%m-%d").date(),
        daily_bias_signals={}, narrative="", checkpoints=[], created_at=now, updated_at=now,
    )
    db.add(plan)
    db.flush()
    scenario = PlanScenarioModel(
        id=str(uuid.uuid4()), plan_id=plan.id, notes="mine", created_at=now, updated_at=now,
    )
    db.add(scenario)
    db.commit()
    return scenario.id


# --- GET/PUT /api/premarket/{date} ---

def test_get_plan_not_found_returns_404(client: TestClient) -> None:
    resp = client.get("/api/premarket/2026-01-01")
    assert resp.status_code == 404


def test_get_plan_invalid_date_returns_422(client: TestClient) -> None:
    resp = client.get("/api/premarket/not-a-date")
    assert resp.status_code == 422


def test_upsert_creates_plan(client: TestClient) -> None:
    resp = client.put("/api/premarket/2026-05-01", json={"daily_bias": "bullish"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["date"] == "2026-05-01"
    assert data["daily_bias"] == "bullish"
    assert data["scenarios"] == []
    assert data["review"] is None


def test_upsert_invalid_daily_bias_returns_422(client: TestClient) -> None:
    resp = client.put("/api/premarket/2026-05-01", json={"daily_bias": "sideways"})
    assert resp.status_code == 422


def test_upsert_idempotent_updates_existing(client: TestClient) -> None:
    client.put("/api/premarket/2026-05-02", json={"daily_bias": "bullish"})
    resp = client.put("/api/premarket/2026-05-02", json={"daily_bias": "bearish"})
    assert resp.status_code == 200
    assert resp.json()["daily_bias"] == "bearish"


def test_upsert_extra_fields_rejected(client: TestClient) -> None:
    resp = client.put("/api/premarket/2026-05-03", json={"unknown_field": True})
    assert resp.status_code == 422


# --- POST /api/premarket/{date}/scenarios ---

def test_create_scenario_requires_existing_plan(client: TestClient) -> None:
    resp = client.post("/api/premarket/2026-05-04/scenarios", json={"notes": "no plan yet"})
    assert resp.status_code == 404


def test_create_scenario_success(client: TestClient) -> None:
    client.put("/api/premarket/2026-05-05", json={})
    resp = client.post("/api/premarket/2026-05-05/scenarios", json={
        "reaction_setup_type": "liquidity_sweep",
        "reaction_setup_detail": "london_high",
        "target_level_type": "fvg",
        "target_level_detail": "1h",
        "notes": "sweep then fvg fill",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["reaction_setup_type"] == "liquidity_sweep"
    assert data["target_level_type"] == "fvg"
    assert data["date"] == "2026-05-05"
    assert data["outcome_status"] is None


def test_create_scenario_mismatched_detail_returns_422(client: TestClient) -> None:
    client.put("/api/premarket/2026-05-06", json={})
    resp = client.post("/api/premarket/2026-05-06/scenarios", json={
        "reaction_setup_type": "liquidity_sweep",
        "reaction_setup_detail": "1h",  # valid for fvg target details, not setup details
    })
    assert resp.status_code == 422


def test_no_cap_on_scenario_count(client: TestClient) -> None:
    client.put("/api/premarket/2026-05-07", json={})
    for _ in range(5):
        resp = client.post("/api/premarket/2026-05-07/scenarios", json={"notes": "x"})
        assert resp.status_code == 201
    plan = client.get("/api/premarket/2026-05-07").json()
    assert len(plan["scenarios"]) == 5


# --- GET/PUT/DELETE /api/premarket/scenarios/{id} ---

def test_get_scenario_not_found_returns_404(client: TestClient) -> None:
    resp = client.get("/api/premarket/scenarios/does-not-exist")
    assert resp.status_code == 404


def test_update_scenario_edits_fields(client: TestClient) -> None:
    client.put("/api/premarket/2026-05-08", json={})
    create_resp = client.post("/api/premarket/2026-05-08/scenarios", json={"notes": "original"})
    scenario_id = create_resp.json()["id"]

    resp = client.put(f"/api/premarket/scenarios/{scenario_id}", json={
        "reaction_setup_type": "unmitigated_fvg",
        "reaction_setup_detail": "1h",
        "notes": "edited",
        "outcome_status": "played_out",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["notes"] == "edited"
    assert data["reaction_setup_type"] == "unmitigated_fvg"
    assert data["outcome_status"] == "played_out"


def test_update_scenario_invalid_outcome_returns_422(client: TestClient) -> None:
    client.put("/api/premarket/2026-05-09", json={})
    create_resp = client.post("/api/premarket/2026-05-09/scenarios", json={"notes": "x"})
    scenario_id = create_resp.json()["id"]

    resp = client.put(f"/api/premarket/scenarios/{scenario_id}", json={
        "notes": "x", "outcome_status": "not_a_real_status",
    })
    assert resp.status_code == 422


def test_delete_scenario_removes_it(client: TestClient) -> None:
    client.put("/api/premarket/2026-05-10", json={})
    create_resp = client.post("/api/premarket/2026-05-10/scenarios", json={"notes": "x"})
    scenario_id = create_resp.json()["id"]

    resp = client.delete(f"/api/premarket/scenarios/{scenario_id}")
    assert resp.status_code == 204
    assert client.get(f"/api/premarket/scenarios/{scenario_id}").status_code == 404


def test_scenario_ownership_isolation(db: Session, client_other_user: TestClient) -> None:
    scenario_id = _make_plan_with_scenario(db, date_="2026-05-11")

    assert client_other_user.get(f"/api/premarket/scenarios/{scenario_id}").status_code == 404
    assert client_other_user.put(
        f"/api/premarket/scenarios/{scenario_id}", json={"notes": "stolen"},
    ).status_code == 404
    assert client_other_user.delete(f"/api/premarket/scenarios/{scenario_id}").status_code == 404


# --- POST /api/premarket/{date}/checkpoint ---

def test_checkpoint_creates_plan_if_absent(client: TestClient) -> None:
    resp = client.post("/api/premarket/2026-05-12/checkpoint", json={"note": "swept asia low"})
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["checkpoints"]) == 1
    assert data["checkpoints"][0]["note"] == "swept asia low"
    assert "timestamp" in data["checkpoints"][0]


def test_checkpoint_is_additive(client: TestClient) -> None:
    client.post("/api/premarket/2026-05-13/checkpoint", json={"note": "first"})
    resp = client.post("/api/premarket/2026-05-13/checkpoint", json={"note": "second"})
    assert resp.status_code == 201
    notes = [c["note"] for c in resp.json()["checkpoints"]]
    assert notes == ["first", "second"]


# --- PUT /api/premarket/{date}/review ---

def test_review_requires_existing_plan(client: TestClient) -> None:
    resp = client.put("/api/premarket/2026-05-14/review", json={"execution_grade": "yes"})
    assert resp.status_code == 404


def test_review_upsert(client: TestClient) -> None:
    client.put("/api/premarket/2026-05-15", json={})
    resp = client.put("/api/premarket/2026-05-15/review", json={"execution_grade": "mostly"})
    assert resp.status_code == 200
    assert resp.json()["execution_grade"] == "mostly"

    plan = client.get("/api/premarket/2026-05-15").json()
    assert plan["review"]["execution_grade"] == "mostly"


def test_review_invalid_grade_returns_422(client: TestClient) -> None:
    client.put("/api/premarket/2026-05-16", json={})
    resp = client.put("/api/premarket/2026-05-16/review", json={"execution_grade": "A"})
    assert resp.status_code == 422


def test_review_idempotent_single_row_per_plan(client: TestClient) -> None:
    client.put("/api/premarket/2026-05-17", json={})
    client.put("/api/premarket/2026-05-17/review", json={"execution_grade": "yes"})
    resp = client.put("/api/premarket/2026-05-17/review", json={"execution_grade": "no"})
    assert resp.status_code == 200
    assert resp.json()["execution_grade"] == "no"


# --- GET /api/premarket (date-range summary list) ---

def test_list_summaries_empty_range(client: TestClient) -> None:
    resp = client.get("/api/premarket", params={"from": "2026-07-01", "to": "2026-07-31"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_summaries_includes_scenario_count(client: TestClient) -> None:
    client.put("/api/premarket/2026-06-10", json={"daily_bias": "bullish"})
    client.post("/api/premarket/2026-06-10/scenarios", json={"notes": "a"})
    client.post("/api/premarket/2026-06-10/scenarios", json={"notes": "b"})

    resp = client.get("/api/premarket", params={"from": "2026-06-01", "to": "2026-06-30"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["date"] == "2026-06-10"
    assert data[0]["daily_bias"] == "bullish"
    assert data[0]["scenario_count"] == 2


def test_list_summaries_excludes_other_users(db: Session, client_other_user: TestClient) -> None:
    _make_plan_with_scenario(db, date_="2026-06-11")
    resp = client_other_user.get("/api/premarket", params={"from": "2026-06-01", "to": "2026-06-30"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_summaries_respects_date_bounds(client: TestClient) -> None:
    client.put("/api/premarket/2026-06-01", json={})
    client.put("/api/premarket/2026-06-30", json={})
    client.put("/api/premarket/2026-07-01", json={})

    resp = client.get("/api/premarket", params={"from": "2026-06-01", "to": "2026-06-30"})
    dates = [d["date"] for d in resp.json()]
    assert dates == ["2026-06-01", "2026-06-30"]


# --- trades.scenario_id ---

def test_trade_can_link_to_scenario(client: TestClient, sample_account: object) -> None:
    client.put("/api/premarket/2026-06-12", json={})
    scenario_id = client.post("/api/premarket/2026-06-12/scenarios", json={"notes": "x"}).json()["id"]

    resp = client.post("/api/trades", json={
        "account_id": sample_account.id,
        "scenario_id": scenario_id,
        "strategy": "mnq-daily",
        "symbol": "MNQ",
        "instrument_type": "futures",
        "direction": "BUY",
        "entry_price": 20000.0,
        "sl_price": 19900.0,
        "tp_price": 20200.0,
        "lot_size": 1.0,
        "open_time": "2026-06-12T13:00:00Z",
        "tags": [],
        "notes": "",
        "metadata": {},
    })
    assert resp.status_code == 201
    assert resp.json()["scenario_id"] == scenario_id


def test_deleting_scenario_does_not_delete_linked_trade(client: TestClient, sample_account: object) -> None:
    client.put("/api/premarket/2026-06-13", json={})
    scenario_id = client.post("/api/premarket/2026-06-13/scenarios", json={"notes": "x"}).json()["id"]

    trade_resp = client.post("/api/trades", json={
        "account_id": sample_account.id,
        "scenario_id": scenario_id,
        "strategy": "mnq-daily",
        "symbol": "MNQ",
        "instrument_type": "futures",
        "direction": "BUY",
        "entry_price": 20000.0,
        "sl_price": 19900.0,
        "tp_price": 20200.0,
        "lot_size": 1.0,
        "open_time": "2026-06-13T13:00:00Z",
        "tags": [],
        "notes": "",
        "metadata": {},
    })
    trade_id = trade_resp.json()["id"]

    client.delete(f"/api/premarket/scenarios/{scenario_id}")
    resp = client.get(f"/api/trades/{trade_id}")
    assert resp.status_code == 200
    assert resp.json()["scenario_id"] == scenario_id
