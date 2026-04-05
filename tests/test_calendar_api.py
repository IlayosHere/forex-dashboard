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

    # Cleanup so other tests start with an empty cache.
    cal_module._cache.pop("current", None)


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

    cal_module._cache.pop("current", None)


# ---------------------------------------------------------------------------
# promoted events
# ---------------------------------------------------------------------------


def test_promoted_event_gets_high_impact_and_flag(client: TestClient) -> None:
    """An event whose name contains a PROMOTED_EVENTS keyword is promoted to High."""
    cal_module._cache.clear()
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

    cal_module._cache.pop("current", None)


def test_non_promoted_medium_event_unchanged(client: TestClient) -> None:
    """A Medium event with no promoted keyword keeps impact=Medium, promoted=False."""
    cal_module._cache.clear()
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

    cal_module._cache.pop("current", None)


def test_high_impact_event_is_not_promoted(client: TestClient) -> None:
    """An already-High event that matches a keyword is NOT marked promoted=True."""
    cal_module._cache.clear()
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

    cal_module._cache.pop("current", None)


# ---------------------------------------------------------------------------
# beat_miss
# ---------------------------------------------------------------------------


def test_beat_miss_beat(client: TestClient) -> None:
    """actual > forecast → beat."""
    cal_module._cache.clear()
    raw = _make_raw_event(actual="2.5%", forecast="2.0%")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["beat_miss"] == "beat"
    cal_module._cache.pop("current", None)


def test_beat_miss_miss(client: TestClient) -> None:
    """actual < forecast → miss."""
    cal_module._cache.clear()
    raw = _make_raw_event(actual="1.8%", forecast="2.0%")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["beat_miss"] == "miss"
    cal_module._cache.pop("current", None)


def test_beat_miss_in_line(client: TestClient) -> None:
    """actual == forecast → in_line."""
    cal_module._cache.clear()
    raw = _make_raw_event(actual="2.0%", forecast="2.0%")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["beat_miss"] == "in_line"
    cal_module._cache.pop("current", None)


def test_beat_miss_no_actual_is_pending(client: TestClient) -> None:
    """No actual value → pending."""
    cal_module._cache.clear()
    raw = _make_raw_event(actual="", forecast="2.0%")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["beat_miss"] == "pending"
    cal_module._cache.pop("current", None)


def test_beat_miss_unparseable_value_is_pending(client: TestClient) -> None:
    """Unparseable actual string → pending."""
    cal_module._cache.clear()
    raw = _make_raw_event(actual="N/A", forecast="2.0%")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["beat_miss"] == "pending"
    cal_module._cache.pop("current", None)


# ---------------------------------------------------------------------------
# session_bucket
# ---------------------------------------------------------------------------


def test_session_bucket_pre_market(client: TestClient) -> None:
    """Event at 08:30 ET → pre_market."""
    cal_module._cache.clear()
    raw = _make_raw_event(date="2025-01-15T08:30:00-05:00")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["session_bucket"] == "pre_market"
    cal_module._cache.pop("current", None)


def test_session_bucket_cash_session(client: TestClient) -> None:
    """Event at 10:00 ET → cash_session."""
    cal_module._cache.clear()
    raw = _make_raw_event(date="2025-01-15T10:00:00-05:00")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["session_bucket"] == "cash_session"
    cal_module._cache.pop("current", None)


def test_session_bucket_open_exact_is_cash_session(client: TestClient) -> None:
    """Event exactly at 09:30 ET is the open — cash_session."""
    cal_module._cache.clear()
    raw = _make_raw_event(date="2025-01-15T09:30:00-05:00")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["session_bucket"] == "cash_session"
    cal_module._cache.pop("current", None)


def test_session_bucket_after_close_is_none(client: TestClient) -> None:
    """Event at 17:00 ET → none."""
    cal_module._cache.clear()
    raw = _make_raw_event(date="2025-01-15T17:00:00-05:00")

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([raw]),
    ):
        resp = client.get("/api/calendar?week=current")

    assert resp.json()[0]["session_bucket"] == "none"
    cal_module._cache.pop("current", None)


# ---------------------------------------------------------------------------
# datetime_et
# ---------------------------------------------------------------------------


def test_datetime_et_present_and_non_empty(client: TestClient) -> None:
    """Every event in the response has a non-empty datetime_et field."""
    cal_module._cache.clear()
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

    cal_module._cache.pop("current", None)


# ---------------------------------------------------------------------------
# HTTP 503
# ---------------------------------------------------------------------------


def test_503_when_fetch_raises(client: TestClient) -> None:
    """Network failure from _fetch_ff_json propagates as HTTP 503."""
    cal_module._cache.clear()

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
    cal_module._cache.clear()

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([]),
    ) as mock_urlopen:
        client.get("/api/calendar?week=current")

    called_url = mock_urlopen.call_args[0][0].full_url
    assert "thisweek" in called_url

    cal_module._cache.pop("current", None)


def test_week_next_calls_nextweek_url(client: TestClient) -> None:
    """?week=next fetches from the nextweek URL."""
    cal_module._cache.clear()

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([]),
    ) as mock_urlopen:
        client.get("/api/calendar?week=next")

    called_url = mock_urlopen.call_args[0][0].full_url
    assert "nextweek" in called_url

    cal_module._cache.pop("next", None)


def test_invalid_week_param_returns_422(client: TestClient) -> None:
    """?week=foo is rejected by the Query pattern validator."""
    resp = client.get("/api/calendar?week=foo")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# default week
# ---------------------------------------------------------------------------


def test_no_week_param_defaults_to_current(client: TestClient) -> None:
    """Omitting ?week defaults to 'current' (thisweek URL)."""
    cal_module._cache.clear()

    with patch(
        "api.routes.calendar.urllib.request.urlopen",
        _urlopen_mock([]),
    ) as mock_urlopen:
        resp = client.get("/api/calendar")

    assert resp.status_code == 200
    called_url = mock_urlopen.call_args[0][0].full_url
    assert "thisweek" in called_url

    cal_module._cache.pop("current", None)
