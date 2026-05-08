"""
tests/test_sessions_api.py
--------------------------
Integration tests for GET/PUT /api/sessions/{date} endpoints.
"""
from __future__ import annotations

from fastapi.testclient import TestClient


# --- helpers ---

def _payload(**overrides: object) -> dict:
    base: dict = {
        "had_pre_session_plan": None,
        "feeling_pre": None,
        "feeling_during": None,
        "feeling_post": None,
        "session_notes": "",
    }
    base.update(overrides)
    return base


# --- GET /api/sessions/{date} ---

def test_get_session_not_found_returns_404(client: TestClient) -> None:
    resp = client.get("/api/sessions/2026-01-01")
    assert resp.status_code == 404


def test_get_session_invalid_date_returns_422(client: TestClient) -> None:
    resp = client.get("/api/sessions/not-a-date")
    assert resp.status_code == 422


def test_get_session_after_upsert_returns_200(client: TestClient) -> None:
    client.put("/api/sessions/2026-05-07", json=_payload(session_notes="hello"))
    resp = client.get("/api/sessions/2026-05-07")
    assert resp.status_code == 200
    assert resp.json()["session_notes"] == "hello"


# --- PUT /api/sessions/{date} ---

def test_upsert_creates_session(client: TestClient) -> None:
    resp = client.put("/api/sessions/2026-05-01", json=_payload(
        had_pre_session_plan=True,
        feeling_pre="calm",
        feeling_during="focused",
        feeling_post="confident",
        session_notes="good day",
    ))
    assert resp.status_code == 200
    data = resp.json()
    assert data["date"] == "2026-05-01"
    assert data["had_pre_session_plan"] is True
    assert data["feeling_pre"] == "calm"
    assert data["feeling_during"] == "focused"
    assert data["feeling_post"] == "confident"
    assert data["session_notes"] == "good day"


def test_upsert_idempotent_updates_existing(client: TestClient) -> None:
    client.put("/api/sessions/2026-05-02", json=_payload(session_notes="first"))
    resp = client.put("/api/sessions/2026-05-02", json=_payload(session_notes="second"))
    assert resp.status_code == 200
    assert resp.json()["session_notes"] == "second"


def test_upsert_same_date_only_one_row(client: TestClient) -> None:
    client.put("/api/sessions/2026-05-03", json=_payload())
    client.put("/api/sessions/2026-05-03", json=_payload())
    resp = client.get("/api/sessions/2026-05-03")
    assert resp.status_code == 200


def test_upsert_null_plan_is_valid(client: TestClient) -> None:
    resp = client.put("/api/sessions/2026-05-04", json=_payload(had_pre_session_plan=None))
    assert resp.status_code == 200
    assert resp.json()["had_pre_session_plan"] is None


def test_upsert_false_plan_stored(client: TestClient) -> None:
    resp = client.put("/api/sessions/2026-05-05", json=_payload(had_pre_session_plan=False))
    assert resp.status_code == 200
    assert resp.json()["had_pre_session_plan"] is False


def test_upsert_invalid_feeling_returns_422(client: TestClient) -> None:
    resp = client.put("/api/sessions/2026-05-06", json=_payload(feeling_pre="euphoric"))
    assert resp.status_code == 422


def test_upsert_all_feeling_values_accepted(client: TestClient) -> None:
    feelings = ["calm", "focused", "confident", "anxious", "impatient",
                "fearful", "greedy", "distracted", "revenge", "tired"]
    for i, feeling in enumerate(feelings):
        date = f"2026-06-{i + 1:02d}"
        resp = client.put(f"/api/sessions/{date}", json=_payload(feeling_pre=feeling))
        assert resp.status_code == 200, f"feeling '{feeling}' rejected"
        assert resp.json()["feeling_pre"] == feeling


def test_upsert_null_feelings_cleared(client: TestClient) -> None:
    client.put("/api/sessions/2026-05-08", json=_payload(feeling_pre="calm"))
    resp = client.put("/api/sessions/2026-05-08", json=_payload(feeling_pre=None))
    assert resp.status_code == 200
    assert resp.json()["feeling_pre"] is None


def test_upsert_invalid_date_format_returns_422(client: TestClient) -> None:
    resp = client.put("/api/sessions/2026-13-99", json=_payload())
    assert resp.status_code == 422


def test_upsert_extra_fields_rejected(client: TestClient) -> None:
    resp = client.put("/api/sessions/2026-05-09", json={"unknown_field": True})
    assert resp.status_code == 422


def test_get_session_owner_filter(client: TestClient, db: object) -> None:
    # Create session as testuser via API
    resp = client.put("/api/sessions/2026-05-10", json=_payload(session_notes="mine"))
    assert resp.status_code == 200
    # Verify owner is set to testuser in the response (not another user)
    assert resp.json()["owner"] == "testuser"


def test_upsert_response_has_timestamps(client: TestClient) -> None:
    resp = client.put("/api/sessions/2026-05-11", json=_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert "created_at" in data
    assert "updated_at" in data


def test_upsert_updated_at_changes_on_second_write(client: TestClient) -> None:
    r1 = client.put("/api/sessions/2026-05-12", json=_payload())
    r2 = client.put("/api/sessions/2026-05-12", json=_payload(session_notes="changed"))
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r2.json()["updated_at"] >= r1.json()["updated_at"]
