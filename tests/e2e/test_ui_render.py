"""
tests/e2e/test_ui_render.py
---------------------------
Validate that the Next.js ui renders and - critically - that
NEXT_PUBLIC_API_URL was baked correctly at build time. Next.js inlines
`NEXT_PUBLIC_*` env vars into the compiled client bundles, so if the
GitHub Actions deploy forgot to pass the build-arg the bundles will
still reference `localhost:8000` and the deployed ui will look fine
until the user tries to do anything. This is the exact bug the
deferred 'custom domain' TODO is trying to remove.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

import httpx

_CHUNK_RE = re.compile(r'/_next/static/[^"\'<> ]+?\.js')


def test_ui_homepage_renders(ui_url: str, client: httpx.Client) -> None:
    """GET / on the ui Cloud Run service returns 200."""
    response = client.get(f"{ui_url}/")
    assert response.status_code == 200, (
        f"GET / returned {response.status_code}: {response.text[:200]}"
    )


def test_next_public_api_url_baked(
    ui_url: str,
    api_url: str,
    client: httpx.Client,
) -> None:
    """Scan the compiled JS bundles for the api hostname.

    We want to prove two things:
      1. At least one /_next/static/*.js chunk references the api host
         (meaning NEXT_PUBLIC_API_URL was baked correctly).
      2. No chunk contains the literal 'localhost:8000' (which would
         mean the build-arg was missed and the default leaked through).
    """
    api_host = urlparse(api_url).hostname
    assert api_host, f"could not parse hostname from api_url={api_url!r}"

    # Start with the login page - it's guaranteed to reference the api.
    page_sources: list[str] = []
    for path in ("/login", "/"):
        resp = client.get(f"{ui_url}{path}")
        assert resp.status_code == 200, (
            f"GET {path} returned {resp.status_code}: {resp.text[:200]}"
        )
        page_sources.append(resp.text)

    chunk_paths: set[str] = set()
    for html in page_sources:
        chunk_paths.update(_CHUNK_RE.findall(html))

    assert chunk_paths, (
        "no /_next/static/*.js chunks found in HTML - cannot verify "
        "NEXT_PUBLIC_API_URL. HTML head snippet: "
        f"{page_sources[0][:500]}"
    )

    found_api_host = False
    localhost_hits: list[str] = []
    for chunk in sorted(chunk_paths):
        url = f"{ui_url}{chunk}"
        resp = client.get(url)
        if resp.status_code != 200:
            continue
        body = resp.text
        if api_host in body:
            found_api_host = True
        if "localhost:8000" in body:
            localhost_hits.append(chunk)

    assert not localhost_hits, (
        f"compiled ui chunks still reference 'localhost:8000' - "
        f"NEXT_PUBLIC_API_URL was not baked correctly. Offending "
        f"chunks: {localhost_hits}"
    )
    assert found_api_host, (
        f"no compiled ui chunk referenced the api hostname {api_host!r}. "
        f"NEXT_PUBLIC_API_URL may not have been passed as a Docker build "
        f"arg. Checked {len(chunk_paths)} chunks."
    )
