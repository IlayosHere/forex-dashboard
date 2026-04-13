"""
tests/e2e/test_runner_liveness.py
---------------------------------
Validate that the always-on forex-runner Cloud Run service is actually
scheduling scans. APScheduler ticks every ~15 minutes at candle close,
so this test is marked `slow` and skipped by default.

Run with:
    pytest tests/e2e/ -v -m slow
"""
from __future__ import annotations

import os
import time

import httpx
import pytest


# Wait just past one APScheduler tick interval.
_WAIT_SECONDS = 16 * 60


@pytest.mark.slow
@pytest.mark.skipif(
    not os.getenv("RUN_SLOW_E2E"),
    reason="slow test (16 min wait); set RUN_SLOW_E2E=1 to enable",
)
def test_runner_scheduling(
    api_url: str,
    auth_headers: dict[str, str],
    client: httpx.Client,
) -> None:
    """Signals list should advance within one scheduler tick window.

    This is a weak signal (new signals only fire on live candle setups),
    so we accept EITHER:
      - total count increased, OR
      - the most recent created_at moved forward.

    If both are unchanged after ~16 minutes the runner is probably not
    scheduling. A stronger check via `gcloud logging read` is left to
    the manual verification step in the plan (section 'Runner health').
    """
    def _snapshot() -> tuple[int, str | None]:
        resp = client.get(
            f"{api_url}/api/signals?limit=200", headers=auth_headers,
        )
        assert resp.status_code == 200, (
            f"GET /api/signals returned {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        # /api/signals is paginated: {"items": [...], "total": N}.
        items = data["items"] if isinstance(data, dict) else data
        latest = None
        if items:
            latest = max(
                (row.get("created_at") or row.get("candle_time") or "")
                for row in items
            ) or None
        return len(items), latest

    before_count, before_latest = _snapshot()
    time.sleep(_WAIT_SECONDS)
    after_count, after_latest = _snapshot()

    advanced = after_count > before_count or (
        after_latest is not None
        and before_latest is not None
        and after_latest > before_latest
    )
    assert advanced, (
        f"runner appears idle after {_WAIT_SECONDS}s: "
        f"count {before_count}->{after_count}, "
        f"latest {before_latest!r}->{after_latest!r}"
    )
