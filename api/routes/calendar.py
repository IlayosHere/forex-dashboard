"""
api/routes/calendar.py
----------------------
GET /api/calendar  — fetch and return economic calendar events from ForexFactory.

Events are fetched from the ForexFactory community JSON feed, cached in memory
for 15 minutes, and enriched with beat/miss logic, session bucketing, and an
impact-promotion rule for events that are officially Medium but trade as High.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from api.schemas import CalendarEventResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["calendar"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FF_URLS: dict[str, str] = {
    "current": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "next": "https://nfs.faireconomy.media/ff_calendar_nextweek.json",
}

PROMOTED_EVENTS: frozenset[str] = frozenset({
    "jolts",
    "average earnings",
    "zew economic sentiment",
    "tokyo cpi",
    "core pce",
    "canada employment",
    "monthly cpi",
})

_CACHE_TTL = timedelta(minutes=15)

# { "current": (data, fetched_at), "next": (data, fetched_at) }
_cache: dict[str, tuple[list[dict[str, Any]], datetime]] = {}

# ET offsets — FF feed embeds the offset directly; we read it back from the
# parsed datetime rather than hardcoding, so DST is handled by the source.
_ET_OPEN_MINUTES = 9 * 60 + 30   # 09:30 ET → 570 min
_ET_CLOSE_MINUTES = 16 * 60      # 16:00 ET → 960 min


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_ff_json(week: str) -> list[dict[str, Any]]:
    """Synchronous HTTP GET of the ForexFactory feed. Called via asyncio.to_thread."""
    url = _FF_URLS[week]
    req = urllib.request.Request(url, headers={"User-Agent": "forex-dashboard/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw: list[dict[str, Any]] = json.loads(resp.read().decode())
    return raw


def _is_promoted(name: str) -> bool:
    """Return True if the event name matches any promoted event substring."""
    lowered = name.lower()
    return any(keyword in lowered for keyword in PROMOTED_EVENTS)


def _effective_impact(ff_impact: str, name: str) -> tuple[str, bool]:
    """Return (impact, promoted) after applying the promotion rule."""
    if ff_impact.lower() == "medium" and _is_promoted(name):
        return "High", True
    return ff_impact.capitalize(), False


def _strip_suffix(value: str) -> float | None:
    """Parse a ForexFactory numeric string to float, stripping % K M B suffixes."""
    cleaned = value.strip().rstrip("%KMBkmb").replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _beat_miss(actual: str | None, forecast: str | None) -> str:
    """Classify actual vs forecast as beat / miss / in_line / pending."""
    if not actual:
        return "pending"
    if not forecast:
        return "pending"
    actual_f = _strip_suffix(actual)
    forecast_f = _strip_suffix(forecast)
    if actual_f is None or forecast_f is None:
        return "pending"
    if actual_f > forecast_f:
        return "beat"
    if actual_f < forecast_f:
        return "miss"
    return "in_line"


def _session_bucket(dt_et: datetime) -> str:
    """Classify event time into pre_market / cash_session / none (ET)."""
    minutes = dt_et.hour * 60 + dt_et.minute
    if minutes < _ET_OPEN_MINUTES:
        return "pre_market"
    if minutes < _ET_CLOSE_MINUTES:
        return "cash_session"
    return "none"


def _make_event_id(currency: str, name: str, datetime_utc: str) -> str:
    """Generate a stable 16-char hex ID for the event."""
    payload = f"{currency}|{name}|{datetime_utc}".encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def _transform_event(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert a single ForexFactory event dict into the API response shape."""
    name: str = raw.get("title", "")
    currency: str = raw.get("country", "")
    ff_impact: str = raw.get("impact", "Low")
    actual: str | None = raw.get("actual") or None
    forecast: str | None = raw.get("forecast") or None
    previous: str | None = raw.get("previous") or None

    # FF already embeds the ET offset in the timestamp
    raw_date: str = raw.get("date", "")
    dt_et = datetime.fromisoformat(raw_date)
    if dt_et.tzinfo is None:
        raise ValueError("naive datetime from feed")
    dt_utc = dt_et.astimezone(timezone.utc)

    datetime_utc = dt_utc.isoformat()
    datetime_et = dt_et.isoformat()

    impact, promoted = _effective_impact(ff_impact, name)

    return {
        "id": _make_event_id(currency, name, datetime_utc),
        "name": name,
        "currency": currency,
        "datetime_utc": datetime_utc,
        "datetime_et": datetime_et,
        "impact": impact,
        "promoted": promoted,
        "previous": previous,
        "forecast": forecast,
        "actual": actual,
        "beat_miss": _beat_miss(actual, forecast),
        "session_bucket": _session_bucket(dt_et),
    }


def _transform_all(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Transform a list of raw FF events, skipping unparseable entries."""
    results: list[dict[str, Any]] = []
    for raw in raw_events:
        try:
            results.append(_transform_event(raw))
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping malformed FF event: %s — %s", raw.get("title"), exc)
    return results


async def _get_events(week: str) -> list[dict[str, Any]]:
    """Return cached events or fetch fresh from ForexFactory."""
    now = datetime.now(timezone.utc)
    cached = _cache.get(week)
    if cached is not None:
        data, fetched_at = cached
        if now - fetched_at < _CACHE_TTL:
            logger.debug("Returning cached calendar for week=%s", week)
            return data

    logger.info("Fetching ForexFactory calendar for week=%s", week)
    raw = await asyncio.to_thread(_fetch_ff_json, week)
    transformed = _transform_all(raw)
    _cache[week] = (transformed, now)
    return transformed


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------

@router.get("/calendar", response_model=list[CalendarEventResponse])
async def get_calendar(
    week: str = Query(default="current", pattern="^(current|next)$"),
) -> list[dict[str, Any]]:
    """Return economic calendar events for the current or next week.

    Events are sourced from the ForexFactory community JSON feed and cached
    in memory for 15 minutes. Impact levels are promoted for selected events
    that trade as High despite their official Medium rating.
    """
    try:
        return await _get_events(week)
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Failed to fetch ForexFactory calendar: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Economic calendar feed unavailable. Please try again shortly.",
        ) from exc
