"""
tests/e2e/test_jwt_auth.py
--------------------------
Validate the JWT login flow end-to-end against the deployed api:

- Login returns an `access_token` (FastAPI OAuth2-style field name,
  confirmed in api/auth.py:LoginResponse).
- Token claims have `sub == E2E_USER` and `exp` in the future.
- Authenticated GET /api/signals works with the token.
- Tampered and missing tokens are both rejected with 401.
- 20 parallel requests with the same token all succeed - this
  exercises multiple Cloud Run instances (stateless JWT validation
  with a shared JWT_SECRET is the whole point).
"""
from __future__ import annotations

import concurrent.futures
import time

import httpx
import pytest
from jose import jwt


def test_login_returns_jwt(
    api_url: str,
    e2e_user: str,
    e2e_password: str,
    client: httpx.Client,
) -> None:
    """POST /api/auth/login happy path returns an access_token field."""
    response = client.post(
        f"{api_url}/api/auth/login",
        json={"username": e2e_user, "password": e2e_password},
    )
    assert response.status_code == 200, (
        f"login returned {response.status_code}: {response.text}"
    )
    payload = response.json()
    assert "access_token" in payload, (
        f"expected 'access_token' field in response: {payload}"
    )
    assert payload.get("token_type") == "bearer", (
        f"expected token_type 'bearer', got: {payload}"
    )
    assert isinstance(payload["access_token"], str) and payload["access_token"]


def test_jwt_claims(auth_token: str, e2e_user: str) -> None:
    """Decode the JWT (without verifying signature) and sanity-check claims."""
    claims = jwt.get_unverified_claims(auth_token)
    assert claims.get("sub") == e2e_user, (
        f"expected sub == {e2e_user!r}, got {claims.get('sub')!r}"
    )
    exp = claims.get("exp")
    assert exp is not None, f"no exp claim in token: {claims}"
    assert exp > time.time(), (
        f"token already expired: exp={exp} now={time.time()}"
    )


def test_authorized_signals_list(
    api_url: str,
    auth_headers: dict[str, str],
    client: httpx.Client,
) -> None:
    """GET /api/signals with a valid Bearer token returns a list."""
    response = client.get(f"{api_url}/api/signals", headers=auth_headers)
    assert response.status_code == 200, (
        f"GET /api/signals returned {response.status_code}: {response.text}"
    )
    body = response.json()
    # /api/signals returns a paginated envelope: {"items": [...], "total": N}.
    assert isinstance(body, dict) and "items" in body, (
        f"expected paginated envelope {{items, total}} from /api/signals, "
        f"got {type(body).__name__}: {body!r}"
    )
    assert isinstance(body["items"], list), (
        f"/api/signals.items is not a list: {body['items']!r}"
    )


def test_tampered_token_rejected(
    api_url: str,
    auth_token: str,
    client: httpx.Client,
) -> None:
    """Flipping the last character of a valid token must yield 401."""
    # Swap the last char for a different one so the signature no longer matches.
    last = auth_token[-1]
    replacement = "A" if last != "A" else "B"
    tampered = auth_token[:-1] + replacement
    response = client.get(
        f"{api_url}/api/signals",
        headers={"Authorization": f"Bearer {tampered}"},
    )
    assert response.status_code == 401, (
        f"tampered token should be rejected; got {response.status_code}: "
        f"{response.text}"
    )


def test_no_token_rejected(api_url: str, client: httpx.Client) -> None:
    """No Authorization header must yield 401."""
    response = client.get(f"{api_url}/api/signals")
    assert response.status_code == 401, (
        f"missing token should yield 401; got {response.status_code}: "
        f"{response.text}"
    )


def test_20_parallel_requests(
    api_url: str,
    auth_headers: dict[str, str],
) -> None:
    """Fire 20 concurrent GET /api/signals to exercise multi-instance JWT validation."""
    url = f"{api_url}/api/signals"

    def _fetch() -> int:
        # Fresh client per worker so threads don't share connection state.
        with httpx.Client(timeout=30.0) as c:
            return c.get(url, headers=auth_headers).status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        results = list(pool.map(lambda _: _fetch(), range(20)))

    failing = [code for code in results if code != 200]
    assert not failing, (
        f"expected all 20 parallel requests to return 200; "
        f"got {len(failing)} non-200 responses: {results}"
    )
