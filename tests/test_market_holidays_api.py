"""
tests/test_market_holidays_api.py
----------------------------------
Tests for GET /api/market-holidays and shared/market_holidays.py.

Covers: pure-function range filtering for CME Globex closures and US-holiday
thin-volume days, route shape/auth, and week=current|next dispatch.
"""
from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from api.routes.market_holidays import _week_range
from shared.market_holidays import cme_holidays_for_range, us_thin_volume_days_for_range

# ---------------------------------------------------------------------------
# shared/market_holidays.py — pure functions
# ---------------------------------------------------------------------------


def test_cme_full_close_on_christmas() -> None:
    """Christmas Day is a full_close with no early_close_et."""
    results = cme_holidays_for_range(date(2026, 12, 22), date(2026, 12, 26))
    christmas = next(r for r in results if r["date"] == "2026-12-25")
    assert christmas["closure_type"] == "full_close"
    assert christmas["early_close_et"] is None


def test_cme_early_close_on_independence_day_observed() -> None:
    """July 3, 2026 (observed Independence Day) is an early_close with a time."""
    results = cme_holidays_for_range(date(2026, 7, 1), date(2026, 7, 5))
    july3 = next(r for r in results if r["date"] == "2026-07-03")
    assert july3["closure_type"] == "early_close"
    assert july3["early_close_et"] == "13:15"


def test_cme_holidays_excludes_dates_outside_range() -> None:
    results = cme_holidays_for_range(date(2026, 6, 16), date(2026, 6, 19))
    assert results == []


def test_thin_volume_includes_juneteenth() -> None:
    """Juneteenth (2026-06-19) is a thin_volume day — NQ trades, CME doesn't close."""
    results = us_thin_volume_days_for_range(date(2026, 6, 16), date(2026, 6, 22))
    juneteenth = next(r for r in results if r["date"] == "2026-06-19")
    assert juneteenth["closure_type"] == "thin_volume"
    assert juneteenth["early_close_et"] is None


def test_thin_volume_excludes_dates_already_in_cme_table() -> None:
    """Christmas Day is a full_close, not also a redundant thin_volume entry."""
    results = us_thin_volume_days_for_range(date(2026, 12, 22), date(2026, 12, 26))
    assert not [r for r in results if r["date"] == "2026-12-25"]


def test_thin_volume_excludes_dates_outside_range() -> None:
    """No US bank holiday between Independence Day and Labor Day."""
    results = us_thin_volume_days_for_range(date(2026, 8, 10), date(2026, 8, 13))
    assert results == []


# ---------------------------------------------------------------------------
# api/routes/market_holidays.py — _week_range
# ---------------------------------------------------------------------------


def test_week_range_current_starts_on_monday() -> None:
    start, end = _week_range("current")
    assert start.weekday() == 0
    assert (end - start).days == 6


def test_week_range_next_is_seven_days_after_current() -> None:
    current_start, _ = _week_range("current")
    next_start, _ = _week_range("next")
    assert (next_start - current_start).days == 7


# ---------------------------------------------------------------------------
# GET /api/market-holidays — route
# ---------------------------------------------------------------------------


def test_get_market_holidays_returns_200(client: TestClient) -> None:
    resp = client.get("/api/market-holidays?week=current")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_market_holidays_entry_shape(client: TestClient) -> None:
    """Whatever entries fall in the current week, each has the expected shape."""
    resp = client.get("/api/market-holidays?week=current")
    assert resp.status_code == 200
    for entry in resp.json():
        assert entry["closure_type"] in {"full_close", "early_close", "thin_volume"}
        assert "id" in entry and "date" in entry and "label" in entry


def test_get_market_holidays_invalid_week_param_422(client: TestClient) -> None:
    resp = client.get("/api/market-holidays?week=bogus")
    assert resp.status_code == 422


def test_get_market_holidays_requires_auth(raw_client: TestClient) -> None:
    resp = raw_client.get("/api/market-holidays?week=current")
    assert resp.status_code == 401
