"""
tests/test_auth_api.py
-----------------------
Integration tests for POST /api/auth/login.
Inserts UserModel rows directly into the test DB to test DB-backed login.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models import UserModel

_KNOWN_PASSWORD = "hunter2"
# Pre-computed bcrypt hash of "hunter2" — avoids slow hash at collection time.
_KNOWN_HASH = "$2b$12$67SobfGqs9AUtJnVdZqt6uJu/YD7Qz2JaMu3dmIkJu64ePi/3n1bS"


def _insert_user(
    db: Session,
    *,
    username: str = "tester",
    password_hash: str = _KNOWN_HASH,
    is_admin: bool = False,
) -> UserModel:
    user = UserModel(
        id=str(uuid.uuid4()),
        username=username,
        password_hash=password_hash,
        is_admin=is_admin,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


def test_login_success_returns_token(db: Session, client: TestClient) -> None:
    _insert_user(db)
    resp = client.post("/api/auth/login", json={"username": "tester", "password": _KNOWN_PASSWORD})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 20


def test_login_wrong_password_returns_401(db: Session, client: TestClient) -> None:
    _insert_user(db)
    resp = client.post("/api/auth/login", json={"username": "tester", "password": "wrongpass"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


def test_login_unknown_user_returns_401(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={"username": "nobody", "password": "anything"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


def test_login_response_has_no_username_field(db: Session, client: TestClient) -> None:
    _insert_user(db)
    resp = client.post("/api/auth/login", json={"username": "tester", "password": _KNOWN_PASSWORD})
    assert resp.status_code == 200
    assert "username" not in resp.json()


def test_login_password_too_long_returns_422(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={"username": "tester", "password": "x" * 129})
    assert resp.status_code == 422


def test_login_empty_username_returns_422(client: TestClient) -> None:
    resp = client.post("/api/auth/login", json={"username": "", "password": "somepass"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# JWT round-trip and rejection tests (use raw_client — real JWT validation)
# ---------------------------------------------------------------------------


def test_protected_endpoint_rejects_missing_token(raw_client: TestClient) -> None:
    """Request with no Authorization header must return 401 with WWW-Authenticate."""
    resp = raw_client.get("/api/trades")
    assert resp.status_code == 401
    assert "Bearer" in resp.headers.get("WWW-Authenticate", "")


def test_protected_endpoint_rejects_invalid_token(raw_client: TestClient) -> None:
    """Request with a malformed/invalid token must return 401."""
    resp = raw_client.get("/api/trades", headers={"Authorization": "Bearer not.a.real.token"})
    assert resp.status_code == 401


def test_login_then_use_token_round_trip(db: Session, raw_client: TestClient) -> None:
    """Login returns a token; that token is accepted by a protected endpoint."""
    _insert_user(db)
    login_resp = raw_client.post(
        "/api/auth/login", json={"username": "tester", "password": _KNOWN_PASSWORD},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    trades_resp = raw_client.get(
        "/api/trades", headers={"Authorization": f"Bearer {token}"},
    )
    assert trades_resp.status_code == 200


def test_login_401_has_www_authenticate_header(db: Session, raw_client: TestClient) -> None:
    """Login failure must include WWW-Authenticate: Bearer header."""
    _insert_user(db)
    resp = raw_client.post(
        "/api/auth/login", json={"username": "tester", "password": "wrong"},
    )
    assert resp.status_code == 401
    assert "Bearer" in resp.headers.get("WWW-Authenticate", "")
