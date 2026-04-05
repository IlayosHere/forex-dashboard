"""
tests/test_calendar_api.py
--------------------------
Tests for GET /api/calendar — ForexFactory economic calendar route.

Covers: cache TTL, promoted events, beat/miss classification,
session bucketing, datetime_et field, HTTP 503 on fetch failure,
week param URL dispatch, and default week behaviour.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import api.routes.calendar as cal_module

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clear_calendar_cache() -> None:
    """Clear the in-memory calendar cache before every test.

    Prevents stale state from leaking between tests even when an assertion
    fails mid-test — which would skip any inline cleanup code.
    """
    cal_module._cache.clear()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_DATE_ET = "2025-01-15T08:30:00-05:00"  # 08:30 ET — pre_market
_CASH_DATE_ET = "2025-01-15T10:00:00-05:00"  # 10:00 ET — cash_session
_AFTER_DATE_ET = "2025-01-15T17:00:00-05:00"  # 17:00 ET — none


def _make_raw_event(
    *,
    title: str = "CPI m/m",
    country: str = "USD",
    impact: str = "High",
    date: str = _BASE_DATE_ET,
    actual: str = "",
    forecast: str = "",
    previous: str = "",
) -> dict:
    """Return a minimal ForexFactory-style raw event dict."""
    return {
        "title": title,
        "country": country,
        "impact": impact,
        "date": date,
        "actual": actual,
        "forecast": forecast,
        "previous": previous,
    }


def _urlopen_mock(events: list[dict]) -> MagicMock:
    """Return a mock that behaves like urllib.request.urlopen context manager."""
    body = json.dumps(events).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    return MagicMock(return_value=mock_resp)


# ---------------------------------------------------------------------------
# cache
# ---------------------------------------------------------------------------


def test_cache_hit_does_not_refetch(client: TestClient) -> None:
    """A fresh cache entry is returned without making a network request."""
    frozen_data = [{"id": "abc123", "name": "cached-event"}]
    fresh_ts = datetime.now(timezone.utc) - timedelta(minutes=5)
    cal_module._cache["current"] = (frozen_data, fresh_ts)

    with patch("api.routes.calendar._fetch_ff_json") as mock_fetch:
        resp = client.get("/api/calendar?week=current")

    assert resp.status_code == 200
    mock_fetch.assert_not_called()
    assert resp.json() == frozen_data


def test_stale_cache_triggers_refetch(client: TestClient) -> None:
    """A cache entry older than 15 min causes a new network fetch."""
    stale_ts = datetime.now(timezone.utc) - timedelta(minutes=20)
    old_data: list[dict] = [{"id": "old", "name": "stale"}]
    cal_module._cache["current"] = (old_data, stale_ts)

    fresh_event = _make_raw_event(title="NFP", actual="200K", forecast="180K")
    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([fresh_event]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.status_code == 200
    events = resp.json()
    assert any(e["name"] == "NFP" for e in events)


# ---------------------------------------------------------------------------
# promoted events
# ---------------------------------------------------------------------------


def test_promoted_event_gets_high_impact_and_flag(client: TestClient) -> None:
    """An event whose name contains a PROMOTED_EVENTS keyword is promoted to High."""
    raw = _make_raw_event(title="JOLTS Job Openings", impact="Medium")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.status_code == 200
    event = resp.json()[0]
    assert event["impact"] == "High"
    assert event["promoted"] is True


def test_non_promoted_medium_event_unchanged(client: TestClient) -> None:
    """A Medium event with no promoted keyword keeps impact=Medium, promoted=False."""
    raw = _make_raw_event(title="Retail Sales m/m", impact="Medium")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.status_code == 200
    event = resp.json()[0]
    assert event["impact"] == "Medium"
    assert event["promoted"] is False


def test_high_impact_event_is_not_promoted(client: TestClient) -> None:
    """An already-High event that matches a keyword is NOT marked promoted=True."""
    # "core pce" is in PROMOTED_EVENTS but impact is already High.
    raw = _make_raw_event(title="Core PCE Price Index m/m", impact="High")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    event = resp.json()[0]
    assert event["impact"] == "High"
    assert event["promoted"] is False


# ---------------------------------------------------------------------------
# beat_miss
# ---------------------------------------------------------------------------


def test_beat_miss_beat(client: TestClient) -> None:
    """actual > forecast → beat."""
    raw = _make_raw_event(actual="2.5%", forecast="2.0%")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["beat_miss"] == "beat"


def test_beat_miss_miss(client: TestClient) -> None:
    """actual < forecast → miss."""
    raw = _make_raw_event(actual="1.8%", forecast="2.0%")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["beat_miss"] == "miss"


def test_beat_miss_in_line(client: TestClient) -> None:
    """actual == forecast → in_line."""
    raw = _make_raw_event(actual="2.0%", forecast="2.0%")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["beat_miss"] == "in_line"


def test_beat_miss_no_actual_is_pending(client: TestClient) -> None:
    """No actual value → pending."""
    raw = _make_raw_event(actual="", forecast="2.0%")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["beat_miss"] == "pending"


def test_beat_miss_unparseable_value_is_pending(client: TestClient) -> None:
    """Unparseable actual string → pending."""
    raw = _make_raw_event(actual="N/A", forecast="2.0%")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["beat_miss"] == "pending"


# ---------------------------------------------------------------------------
# session_bucket
# ---------------------------------------------------------------------------


def test_session_bucket_pre_market(client: TestClient) -> None:
    """Event at 08:30 ET → pre_market."""
    raw = _make_raw_event(date="2025-01-15T08:30:00-05:00")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["session_bucket"] == "pre_market"


def test_session_bucket_cash_session(client: TestClient) -> None:
    """Event at 10:00 ET → cash_session."""
    raw = _make_raw_event(date="2025-01-15T10:00:00-05:00")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["session_bucket"] == "cash_session"


def test_session_bucket_open_exact_is_cash_session(client: TestClient) -> None:
    """Event exactly at 09:30 ET is the open — cash_session."""
    raw = _make_raw_event(date="2025-01-15T09:30:00-05:00")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["session_bucket"] == "cash_session"


def test_session_bucket_after_close_is_none(client: TestClient) -> None:
    """Event at 17:00 ET → none."""
    raw = _make_raw_event(date="2025-01-15T17:00:00-05:00")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["session_bucket"] == "none"


# ---------------------------------------------------------------------------
# datetime_et
# ---------------------------------------------------------------------------


def test_datetime_et_present_and_non_empty(client: TestClient) -> None:
    """Every event in the response has a non-empty datetime_et field."""
    raw = _make_raw_event(date="2025-01-15T08:30:00-05:00")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.status_code == 200
    for event in resp.json():
        assert "datetime_et" in event
        assert event["datetime_et"]  # non-empty string


# ---------------------------------------------------------------------------
# HTTP 503
# ---------------------------------------------------------------------------


def test_503_when_fetch_raises(client: TestClient) -> None:
    """Network failure from _fetch_ff_json propagates as HTTP 503."""
    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        side_effect=OSError("Connection refused"),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# week param
# ---------------------------------------------------------------------------


def test_week_current_calls_thisweek_url(client: TestClient) -> None:
    """?week=current fetches from the thisweek URL."""
    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([]),
    ) as mock_urlopen:
        client.get("/api/calendar?week=current")

    called_url = mock_urlopen.call_args[0][0].full_url
    assert "thisweek" in called_url


def test_week_next_calls_nextweek_url(client: TestClient) -> None:
    """?week=next fetches from the nextweek URL."""
    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([]),
    ) as mock_urlopen:
        client.get("/api/calendar?week=next")

    called_url = mock_urlopen.call_args[0][0].full_url
    assert "nextweek" in called_url


def test_invalid_week_param_returns_422(client: TestClient) -> None:
    """?week=foo is rejected by the Query pattern validator."""
    resp = client.get("/api/calendar?week=foo")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# default week
# ---------------------------------------------------------------------------


def test_no_week_param_defaults_to_current(client: TestClient) -> None:
    """Omitting ?week defaults to 'current' (thisweek URL)."""
    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([]),
    ) as mock_urlopen:
        resp = client.get("/api/calendar")

    assert resp.status_code == 200
    called_url = mock_urlopen.call_args[0][0].full_url
    assert "thisweek" in called_url


# ---------------------------------------------------------------------------
# JSON decode error → 503
# ---------------------------------------------------------------------------


def test_503_when_response_is_not_json(client: TestClient) -> None:
    """Non-JSON response (e.g. Cloudflare HTML) propagates as HTTP 503."""
    with patch(
        "api.routes.calendar._fetch_ff_json",
        side_effect=json.JSONDecodeError("msg", "", 0),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# _transform_all skips malformed events
# ---------------------------------------------------------------------------


def test_transform_all_skips_malformed_event() -> None:
    """_transform_all returns only valid events when one is missing required fields."""
    valid_event = _make_raw_event(title="CPI m/m", date=_BASE_DATE_ET)
    # Missing "date" key — _transform_event raises KeyError or ValueError on fromisoformat("")
    malformed_event = {
        "title": "Bad Event",
        "country": "USD",
        "impact": "High",
        # "date" key intentionally absent
        "actual": "",
        "forecast": "",
        "previous": "",
    }

    results = cal_module._transform_all([valid_event, malformed_event])

    assert len(results) == 1
    assert results[0]["name"] == "CPI m/m"
