"""
api/services/trade_stats_mistakes.py
-------------------------------------
Pure functions for per-mistake trade statistics: flat aggregation and
weekly/monthly period bucketing. No DB access, no side effects.

Date bucketing is done in Python (not SQL date functions) so behavior is
identical across SQLite (dev) and PostgreSQL (prod) — see
trade_stats_extended.build_daily_summary / _calc_consistency for the same
pattern applied to day and ISO-week grouping.
"""
from __future__ import annotations

import calendar
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

from api.models import TradeMistakeModel, TradeModel

logger = logging.getLogger(__name__)

_MONDAY_ISO_WEEKDAY = 1
_WEEK_END_OFFSET_DAYS = 6
_VALID_GRANULARITIES = ("week", "month")


def aggregate_mistakes(
    trade_map: dict[str, TradeModel],
    links: list[TradeMistakeModel],
    name_map: dict[str, str],
) -> list[dict[str, Any]]:
    """Aggregate mistake links into per-mistake win/loss/P&L stats.

    Groups `links` by mistake_id, looking up each linked trade in `trade_map`
    (links whose trade is missing are skipped). Returns rows sorted by
    total_pnl_usd ascending (worst P&L first).
    """
    buckets: dict[str, dict[str, Any]] = {}
    for lnk in links:
        trade = trade_map.get(lnk.trade_id)
        if trade is None:
            continue
        mid = lnk.mistake_id
        if mid not in buckets:
            buckets[mid] = {
                "name": name_map.get(mid, mid),
                "count": 0, "wins": 0, "losses": 0,
                "_rr": [], "total_pnl_usd": 0.0, "_trades": [],
            }
        b = buckets[mid]
        b["count"] += 1
        if trade.outcome == "win":
            b["wins"] += 1
        elif trade.outcome == "loss":
            b["losses"] += 1
        b["total_pnl_usd"] += trade.pnl_usd or 0.0
        if trade.rr_achieved is not None and trade.outcome in ("win", "loss"):
            b["_rr"].append(trade.rr_achieved)
        b["_trades"].append(trade)

    result = [_finalize_bucket(b) for b in buckets.values()]
    result.sort(key=lambda x: x["total_pnl_usd"])
    return result


def _trade_ref(trade: TradeModel) -> dict[str, Any]:
    """Build a lightweight MistakeTradeRef dict from a trade."""
    return {
        "id": trade.id,
        "date": trade.open_time.date().isoformat() if trade.open_time else "",
        "symbol": trade.symbol,
        "outcome": trade.outcome,
        "pnl_usd": trade.pnl_usd,
    }


def _finalize_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    """Compute win_rate/avg_rr/avg_pnl_usd from a raw mistake bucket."""
    denom = bucket["wins"] + bucket["losses"]
    rr_list = bucket["_rr"]
    trades = sorted(bucket["_trades"], key=lambda t: t.open_time or datetime.min, reverse=True)
    return {
        "name": bucket["name"],
        "count": bucket["count"],
        "wins": bucket["wins"],
        "losses": bucket["losses"],
        "win_rate": round(bucket["wins"] / denom * 100, 1) if denom > 0 else None,
        "avg_rr": round(sum(rr_list) / len(rr_list), 2) if rr_list else None,
        "total_pnl_usd": round(bucket["total_pnl_usd"], 2),
        "avg_pnl_usd": (
            round(bucket["total_pnl_usd"] / bucket["count"], 2)
            if bucket["count"] > 0 else None
        ),
        "trades": [_trade_ref(t) for t in trades],
    }


def _week_bounds(open_time: datetime) -> tuple[str, str, str]:
    """Return (period label, period_start, period_end) for an ISO week."""
    iso_year, iso_week, _ = open_time.isocalendar()
    period = f"{iso_year}-W{iso_week:02d}"
    start = date.fromisocalendar(iso_year, iso_week, _MONDAY_ISO_WEEKDAY)
    end = start + timedelta(days=_WEEK_END_OFFSET_DAYS)
    return period, start.isoformat(), end.isoformat()


def _month_bounds(open_time: datetime) -> tuple[str, str, str]:
    """Return (period label, period_start, period_end) for a calendar month."""
    period = open_time.strftime("%Y-%m")
    start = date(open_time.year, open_time.month, 1)
    last_day = calendar.monthrange(open_time.year, open_time.month)[1]
    end = date(open_time.year, open_time.month, last_day)
    return period, start.isoformat(), end.isoformat()


def _period_key(open_time: datetime, granularity: str) -> tuple[str, str, str]:
    """Dispatch to the week or month bounds helper for open_time."""
    if granularity == "week":
        return _week_bounds(open_time)
    return _month_bounds(open_time)


def build_mistake_timeseries(
    trades: list[TradeModel],
    links: list[TradeMistakeModel],
    name_map: dict[str, str],
    granularity: str,
) -> list[dict[str, Any]]:
    """Bucket mistake occurrences into weekly or monthly periods.

    Groups `links` by the ISO week or calendar month that their linked
    trade's open_time falls into (links whose trade has open_time=None are
    skipped). Returns periods in chronological ascending order, each with a
    per-mistake breakdown from aggregate_mistakes plus distinct-trade totals.

    Raises ValueError if granularity is neither "week" nor "month".
    """
    if granularity not in _VALID_GRANULARITIES:
        raise ValueError(f"Invalid granularity: {granularity!r}")

    trade_map = {t.id: t for t in trades}
    period_links: dict[str, list[TradeMistakeModel]] = defaultdict(list)
    period_bounds: dict[str, tuple[str, str]] = {}
    for lnk in links:
        trade = trade_map.get(lnk.trade_id)
        if trade is None or trade.open_time is None:
            continue
        key, start, end = _period_key(trade.open_time, granularity)
        period_links[key].append(lnk)
        period_bounds[key] = (start, end)

    return [
        _build_period_bucket(key, period_bounds[key], period_links[key], trade_map, name_map)
        for key in sorted(period_bounds)
    ]


def _build_period_bucket(
    period: str,
    bounds: tuple[str, str],
    bucket_links: list[TradeMistakeModel],
    trade_map: dict[str, TradeModel],
    name_map: dict[str, str],
) -> dict[str, Any]:
    """Build a single MistakePeriodBucket dict from one period's links."""
    start, end = bounds
    mistake_trade_ids = {lnk.trade_id for lnk in bucket_links}
    total_pnl = sum(trade_map[tid].pnl_usd or 0.0 for tid in mistake_trade_ids)
    return {
        "period": period,
        "period_start": start,
        "period_end": end,
        "total_mistake_trades": len(mistake_trade_ids),
        "total_pnl_usd": round(total_pnl, 2),
        "mistakes": aggregate_mistakes(trade_map, bucket_links, name_map),
    }
