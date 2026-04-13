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
    """The Next.js /login route should serve the app shell with the page title."""
    response = client.get(f"{ui_url}/login")
    assert response.status_code == 200, (
        f"GET /login returned {response.status_code}: {response.text[:200]}"
    )
    body = response.text
    # Next.js 16 hydrates the form client-side so the "Sign in" button
    # label is NOT in the initial SSR HTML. The <title> tag IS emitted
    # server-side from the app layout and is the stable liveness marker.
    assert "Forex Signal Dashboard" in body, (
        f"/login body did not contain 'Forex Signal Dashboard' title: {body[:500]}"
    )
