"""
api/services/trade_stats_news.py
----------------------------------
News-day and market-holiday breakdowns for backtest-mode trade statistics.
Pure functions — no DB access, no side effects.

Each aggregator takes a precomputed `date -> bucket label` map (built once by
the caller from shared/economic_calendar.py or shared/market_holidays.py, not
per-trade) and classifies each trade's open_time.date() against it via the
shared aggregate_dimension() helper.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any

from api.models import TradeModel
from api.services.trade_stats_extended import aggregate_dimension

logger = logging.getLogger(__name__)

_NEWS_BUCKET_NAMES: dict[str, str] = {
    "high": "High-impact news day",
    "medium": "Medium-impact news day",
    "normal": "Normal day",
}

_HOLIDAY_BUCKET_NAMES: dict[str, str] = {
    "full_close": "Full closure",
    "early_close": "Early close",
    "thin_volume": "Thin volume",
    "normal": "Normal day",
}


def aggregate_by_news_day(
    closed: list[TradeModel], news_days: dict[date, str],
) -> dict[str, dict]:
    """Group closed trades by whether their day had a high/medium news event.

    Buckets: 'high', 'medium', 'normal'. A day with both a high- and a
    medium-impact event is bucketed as 'high' (the more decision-relevant one).
    """
    def key_fn(t: TradeModel) -> str | None:
        if not t.open_time:
            return None
        return news_days.get(t.open_time.date(), "normal")

    raw = aggregate_dimension(closed, key_fn)
    return {k: {**v, "name": _NEWS_BUCKET_NAMES.get(k, k)} for k, v in raw.items()}


def aggregate_by_market_holiday(
    closed: list[TradeModel], holiday_days: dict[date, str],
) -> dict[str, dict]:
    """Group closed trades by whether their day was a CME closure/thin-volume day.

    Buckets: 'full_close', 'early_close', 'thin_volume', 'normal'.
    """
    def key_fn(t: TradeModel) -> str | None:
        if not t.open_time:
            return None
        return holiday_days.get(t.open_time.date(), "normal")

    raw = aggregate_dimension(closed, key_fn)
    return {k: {**v, "name": _HOLIDAY_BUCKET_NAMES.get(k, k)} for k, v in raw.items()}


def build_news_day_map(start: date, end: date) -> dict[date, str]:
    """date -> 'high'|'medium' for every day in [start, end] with a news event.

    A day with both impact levels collapses to 'high'.
    """
    from shared.economic_calendar import economic_events_for_range

    result: dict[date, str] = {}
    for entry in economic_events_for_range(start, end):
        day = date.fromisoformat(entry["date"])
        if result.get(day) != "high":
            result[day] = entry["impact"]
    return result


def build_holiday_day_map(start: date, end: date) -> dict[date, str]:
    """date -> 'full_close'|'early_close'|'thin_volume' for every closure day."""
    from shared.market_holidays import cme_holidays_for_range, us_thin_volume_days_for_range

    result: dict[date, str] = {}
    for entry in (*cme_holidays_for_range(start, end), *us_thin_volume_days_for_range(start, end)):
        result[date.fromisoformat(entry["date"])] = entry["closure_type"]
    return result


def news_events_by_date(start: date, end: date) -> dict[date, list[dict[str, str]]]:
    """date -> full news-event entries (name/impact/currency), for the day-sheet."""
    from shared.economic_calendar import economic_events_for_range

    result: dict[date, list[dict[str, str]]] = {}
    for entry in economic_events_for_range(start, end):
        day = date.fromisoformat(entry["date"])
        result.setdefault(day, []).append(entry)
    return result


def holiday_events_by_date(start: date, end: date) -> dict[date, list[dict[str, Any]]]:
    """date -> full holiday/closure entries (label/closure_type/note), for the day-sheet."""
    from shared.market_holidays import cme_holidays_for_range, us_thin_volume_days_for_range

    result: dict[date, list[dict[str, Any]]] = {}
    for entry in (*cme_holidays_for_range(start, end), *us_thin_volume_days_for_range(start, end)):
        day = date.fromisoformat(entry["date"])
        result.setdefault(day, []).append(entry)
    return result
