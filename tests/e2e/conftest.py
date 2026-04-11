"""
tests/e2e/conftest.py
---------------------
Fixtures for the end-to-end test suite that runs against a deployed
Cloud Run environment. Every fixture reads from env vars; if any are
missing the whole suite is skipped with a clear message so that a
plain `pytest` invocation (no deployed env) never reports failures.

Required environment variables:
    API_URL       - Base URL of forex-api Cloud Run service
    UI_URL        - Base URL of forex-ui Cloud Run service
    E2E_USER      - Username of the dedicated e2e test user
    E2E_PASSWORD  - Password for the e2e test user

Optional:
    CORS_STRICT=true   - Opt-in to the negative CORS test case. Skip
                         otherwise since a wildcard bootstrap config
                         would produce a spurious failure.

Markers:
    slow - long-running tests (runner scheduling). Run with:
           pytest tests/e2e/ -v -m slow
"""
from __future__ import annotations

import os

import httpx
import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers used by the e2e suite."""
    config.addinivalue_line(
        "markers",
        "slow: long-running e2e tests (minutes). Enable with `-m slow`.",
    )


def _require_env(name: str) -> str:
    """Return an env var or skip the whole module with a clear message."""
    value = os.getenv(name)
    if not value:
        pytest.skip(
            f"{name} env var not set - e2e suite requires a deployed "
            f"environment. Set API_URL, UI_URL, E2E_USER, E2E_PASSWORD.",
            allow_module_level=True,
        )
    return value


@pytest.fixture(scope="session")
def api_url() -> str:
    """Base URL of the forex-api Cloud Run service (no trailing slash)."""
    return _require_env("API_URL").rstrip("/")


@pytest.fixture(scope="session")
def ui_url() -> str:
    """Base URL of the forex-ui Cloud Run service (no trailing slash)."""
    return _require_env("UI_URL").rstrip("/")


@pytest.fixture(scope="session")
def e2e_user() -> str:
    """Username of the dedicated e2e test user seeded via AUTH_USERS."""
    return _require_env("E2E_USER")


@pytest.fixture(scope="session")
def e2e_password() -> str:
    """Password for the e2e test user."""
    return _require_env("E2E_PASSWORD")


@pytest.fixture(scope="session")
def client() -> httpx.Client:
    """Session-scoped httpx client with sensible timeouts for Cloud Run."""
    with httpx.Client(timeout=30.0, follow_redirects=True) as c:
        yield c


@pytest.fixture(scope="module")
def auth_token(
    api_url: str,
    e2e_user: str,
    e2e_password: str,
    client: httpx.Client,
) -> str:
    """Log in once per module and cache the JWT access token."""
    url = f"{api_url}/api/auth/login"
    response = client.post(
        url,
        json={"username": e2e_user, "password": e2e_password},
    )
    assert response.status_code == 200, (
        f"login failed: got {response.status_code}: {response.text}"
    )
    payload = response.json()
    token = payload.get("access_token")
    assert token, f"no access_token in login response: {payload}"
    return token


@pytest.fixture(scope="module")
def auth_headers(auth_token: str) -> dict[str, str]:
    """Authorization header built from the cached JWT."""
    return {"Authorization": f"Bearer {auth_token}"}
