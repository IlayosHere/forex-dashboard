"""
tests/e2e/test_infra_liveness.py
--------------------------------
Smoke checks that the three Cloud Run services are reachable and
serving the expected surfaces. These are the cheapest possible
signals that a deploy succeeded.
"""
from __future__ import annotations

import httpx


def test_api_docs_endpoint(api_url: str, client: httpx.Client) -> None:
    """The FastAPI /docs page should serve the OpenAPI UI."""
    response = client.get(f"{api_url}/docs")
    assert response.status_code == 200, (
        f"GET /docs returned {response.status_code}: {response.text[:200]}"
    )
    body = response.text.lower()
    assert "openapi" in body or "swagger" in body, (
        f"/docs body did not contain 'openapi' or 'swagger' marker: "
        f"{body[:200]}"
    )


def test_ui_login_page(ui_url: str, client: httpx.Client) -> None:
    """The Next.js /login route should render with the stable 'Sign in' marker."""
    response = client.get(f"{ui_url}/login")
    assert response.status_code == 200, (
        f"GET /login returned {response.status_code}: {response.text[:200]}"
    )
    body = response.text
    # "Sign in" is the submit-button label in ui/app/login/page.tsx.
    # This is more stable than looking for "login" substring which
    # could match incidental copy or disappear behind i18n.
    assert "Sign in" in body, (
        f"/login body did not contain 'Sign in' marker: {body[:500]}"
    )
