"""
api/routes/market_holidays.py
------------------------------
GET /api/market-holidays — CME Globex closures/early-closes and US-holiday
thin-volume days for NQ, for the current or next week.

Unlike /api/calendar, this is pure in-memory computation over offline data
(shared/market_holidays.py) — no network fetch, no TTL cache, no 503 path.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from api.auth import get_current_user
from api.schemas import MarketHolidayResponse
from shared.market_holidays import cme_holidays_for_range, us_thin_volume_days_for_range

router = APIRouter(tags=["market-holidays"])


def _week_range(week: str) -> tuple[date, date]:
    """Return the Mon-Sun UTC date range for the current or next week."""
    today = datetime.now(timezone.utc).date()
    monday = today - timedelta(days=today.weekday())
    if week == "next":
        monday += timedelta(days=7)
    return monday, monday + timedelta(days=6)


def _make_holiday_id(date_str: str, label: str) -> str:
    """Generate a stable 16-char hex ID for the holiday entry."""
    payload = f"{date_str}|{label}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def _to_response(raw: dict[str, Any]) -> dict[str, Any]:
    return {"id": _make_holiday_id(raw["date"], raw["label"]), **raw}


@router.get("/market-holidays", response_model=list[MarketHolidayResponse])
def get_market_holidays(
    _: Annotated[str, Depends(get_current_user)],
    week: str = Query(default="current", pattern="^(current|next)$"),
) -> list[dict[str, Any]]:
    """Return CME Globex closures and US-holiday thin-volume days for NQ.

    Pure computation over offline data — no network call, so unlike
    /api/calendar there is no failure path to handle.
    """
    start, end = _week_range(week)
    entries = cme_holidays_for_range(start, end) + us_thin_volume_days_for_range(start, end)
    return [_to_response(h) for h in entries]
