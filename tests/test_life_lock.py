"""
tests/test_life_lock.py
------------------------
Integration tests for the /life second-factor passphrase gate:
POST /api/life/unlock and the require_life_unlock dependency applied to
all /api/life/* routes.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from tests.conftest import TEST_LIFE_PASSPHRASE, TEST_USER, TEST_USER_2

_ALGORITHM = "HS256"


def _mint_token(*, sub: str, scope: str | None, expired: bool = False) -> str:
    """Build a JWT with the given claims, signed with the test JWT_SECRET."""
    delta = timedelta(hours=-1) if expired else timedelta(hours=1)
    payload: dict[str, object] = {"sub": sub, "exp": datetime.now(timezone.utc) + delta}
    if scope is not None:
        payload["scope"] = scope
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=_ALGORITHM)


# ---------------------------------------------------------------------------
# require_life_unlock — gates GET /api/life/entries (representative of all 7)
# ---------------------------------------------------------------------------


def test_no_unlock_header_returns_403(client: TestClient) -> None:
    resp = client.get("/api/life/entries")
    assert resp.status_code == 403


def test_valid_unlock_token_grants_access(life_client: TestClient) -> None:
    resp = life_client.get("/api/life/entries")
    assert resp.status_code == 200


def test_main_jwt_without_scope_claim_rejected(client: TestClient) -> None:
    """A regular app JWT (no `scope` claim) must not double as an unlock token."""
    token = _mint_token(sub=TEST_USER, scope=None)
    resp = client.get("/api/life/entries", headers={"X-Life-Unlock": token})
    assert resp.status_code == 403


def test_wrong_scope_rejected(client: TestClient) -> None:
    token = _mint_token(sub=TEST_USER, scope="not-life")
    resp = client.get("/api/life/entries", headers={"X-Life-Unlock": token})
    assert resp.status_code == 403


def test_token_for_different_user_rejected(client_other_user: TestClient) -> None:
    """A life token minted for TEST_USER must not unlock the app for TEST_USER_2."""
    token = _mint_token(sub=TEST_USER, scope="life")
    resp = client_other_user.get("/api/life/entries", headers={"X-Life-Unlock": token})
    assert resp.status_code == 403


def test_expired_unlock_token_rejected(client: TestClient) -> None:
    token = _mint_token(sub=TEST_USER, scope="life", expired=True)
    resp = client.get("/api/life/entries", headers={"X-Life-Unlock": token})
    assert resp.status_code == 403


def test_unconfigured_password_hash_fails_closed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LIFE_PASSWORD_HASH", "")
    token = _mint_token(sub=TEST_USER, scope="life")
    resp = client.get("/api/life/entries", headers={"X-Life-Unlock": token})
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# POST /api/life/unlock
# ---------------------------------------------------------------------------


def test_unlock_requires_main_app_login(raw_client: TestClient) -> None:
    """Without a Bearer token at all, unlock is a 401 — it's a second factor,
    not a standalone lock."""
    resp = raw_client.post("/api/life/unlock", json={"passphrase": TEST_LIFE_PASSPHRASE})
    assert resp.status_code == 401


def test_unlock_wrong_passphrase_returns_403(client: TestClient) -> None:
    resp = client.post("/api/life/unlock", json={"passphrase": "wrong"})
    assert resp.status_code == 403


def test_unlock_correct_passphrase_returns_token(client: TestClient) -> None:
    resp = client.post("/api/life/unlock", json={"passphrase": TEST_LIFE_PASSPHRASE})
    assert resp.status_code == 200
    data = resp.json()
    assert "unlock_token" in data
    assert data["expires_in_hours"] == 12


def test_unlock_rate_limited_after_five_attempts(client: TestClient) -> None:
    for _ in range(4):
        assert client.post("/api/life/unlock", json={"passphrase": "wrong"}).status_code == 403
    fifth = client.post("/api/life/unlock", json={"passphrase": "wrong"})
    assert fifth.status_code == 429


def test_unlock_token_then_used_across_all_life_routes(life_client: TestClient) -> None:
    assert life_client.get("/api/life/entries").status_code == 200
    assert life_client.get("/api/life/summary").status_code == 200
    assert life_client.get("/api/life/tags").status_code == 200
    created = life_client.post("/api/life/entries", json={"body": "hello"})
    assert created.status_code == 201
