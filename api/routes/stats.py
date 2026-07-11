"""
api/routes/stats.py
-------------------
Extended statistics endpoints for the trade journal.

GET /api/trades/stats/equity-curve   - cumulative P&L over time
GET /api/trades/stats/daily-summary  - daily aggregated stats for heatmap
GET /api/trades/stats/ict            - ICT breakdown for MNQ futures trades
GET /api/trades/stats/rolling-pf     - rolling profit factor (backtest mode)
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import MistakeModel, TradeMistakeModel, TradeModel
from api.schemas_stats import (
    DailySummaryPoint,
    EquityCurvePoint,
    IctStatsResponse,
    MistakeStatResponse,
    RollingExpectancyPoint,
    RollingPfPoint,
)
from api.services.trade_filters import StatsFilterParams
from api.services.trade_helpers import apply_trade_filters
from api.services.trade_stats_extended import (
    build_daily_summary,
    build_equity_curve,
)
from api.services.trade_stats_ict import compute_ict_stats
from api.services.trade_stats_robustness import compute_rolling_pf

logger = logging.getLogger(__name__)

router = APIRouter()


def _fetch_closed_trades(
    current_user: str,
    db: Session,
    filters: StatsFilterParams,
) -> list[TradeModel]:
    """Query closed/breakeven trades with filters applied."""
    stmt = select(TradeModel).where(TradeModel.owner == current_user)
    stmt = apply_trade_filters(stmt, filters)
    stmt = stmt.where(TradeModel.status.in_(("closed", "breakeven")))
    return list(db.scalars(stmt).all())


@router.get(
    "/trades/stats/equity-curve",
    response_model=list[EquityCurvePoint],
)
def equity_curve(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[StatsFilterParams, Depends()],
) -> list[dict]:
    """Return cumulative P&L over time for the equity curve chart."""
    closed = _fetch_closed_trades(current_user, db, filters)
    return build_equity_curve(closed)


@router.get(
    "/trades/stats/daily-summary",
    response_model=list[DailySummaryPoint],
)
def daily_summary(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[StatsFilterParams, Depends()],
) -> list[dict]:
    """Return daily aggregated stats for calendar heatmap."""
    closed = _fetch_closed_trades(current_user, db, filters)
    return build_daily_summary(closed)


@router.get(
    "/trades/stats/ict",
    response_model=IctStatsResponse,
)
def ict_stats(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[StatsFilterParams, Depends()],
) -> dict:
    """Return ICT breakdown statistics for MNQ/MES futures trades.

    Implicitly filters to futures instruments (MNQ + MES) unless instrument_type overridden.
    Supports the same account_type/exclude_account_type filters as other stats endpoints.
    """
    stmt = select(TradeModel).where(TradeModel.owner == current_user)
    if not filters.instrument_type:
        stmt = stmt.where(
            TradeModel.instrument_type.in_(("futures", "futures_mnq", "futures_mes")),
        )
    stmt = apply_trade_filters(stmt, filters)
    trades = list(db.scalars(stmt).all())
    logger.debug("ict_stats: fetched %d MNQ/MES trades for user %s", len(trades), current_user)
    return compute_ict_stats(trades)


@router.get(
    "/trades/stats/rolling-pf",
    response_model=list[RollingPfPoint],
)
def rolling_pf(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[StatsFilterParams, Depends()],
) -> list[dict]:
    """Return rolling profit factor over a 20-trade sliding window."""
    closed = _fetch_closed_trades(current_user, db, filters)
    return compute_rolling_pf(closed)


@router.get(
    "/trades/stats/mistakes",
    response_model=list[MistakeStatResponse],
)
def mistake_stats(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[StatsFilterParams, Depends()],
) -> list[dict]:
    """Return per-mistake cost analysis for closed/breakeven trades.

    Only live-mode trades (non-backtest). Sorted worst P&L first.
    """
    from sqlalchemy import select
    closed = _fetch_closed_trades(current_user, db, filters)
    closed_ids = {t.id for t in closed}
    if not closed_ids:
        return []

    links = list(db.scalars(
        select(TradeMistakeModel).where(TradeMistakeModel.trade_id.in_(closed_ids)),
    ).all())
    if not links:
        return []

    trade_map = {t.id: t for t in closed}
    mistake_ids = {lnk.mistake_id for lnk in links}
    mistakes = list(db.scalars(
        select(MistakeModel).where(MistakeModel.id.in_(mistake_ids)),
    ).all())
    name_map = {m.id: m.name for m in mistakes}

    buckets: dict[str, dict] = {}
    for lnk in links:
        trade = trade_map.get(lnk.trade_id)
        if trade is None:
            continue
        mid = lnk.mistake_id
        if mid not in buckets:
            buckets[mid] = {
                "name": name_map.get(mid, mid),
                "count": 0, "wins": 0, "losses": 0,
                "_rr": [], "total_pnl_usd": 0.0,
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

    result = []
    for b in buckets.values():
        denom = b["wins"] + b["losses"]
        rr_list = b.pop("_rr")
        result.append({
            "name": b["name"],
            "count": b["count"],
            "wins": b["wins"],
            "losses": b["losses"],
            "win_rate": round(b["wins"] / denom * 100, 1) if denom > 0 else None,
            "avg_rr": round(sum(rr_list) / len(rr_list), 2) if rr_list else None,
            "total_pnl_usd": round(b["total_pnl_usd"], 2),
            "avg_pnl_usd": round(b["total_pnl_usd"] / b["count"], 2) if b["count"] > 0 else None,
        })
    result.sort(key=lambda x: x["total_pnl_usd"])
    return result


@router.get(
    "/trades/stats/rolling-expectancy",
    response_model=list[RollingExpectancyPoint],
)
def rolling_expectancy(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[StatsFilterParams, Depends()],
    window: int = Query(default=30, ge=5, le=200),
) -> list[dict]:
    """Return rolling expectancy over a sliding window of trades."""
    closed = _fetch_closed_trades(current_user, db, filters)
    from api.services.trade_stats_live import compute_rolling_expectancy
    return compute_rolling_expectancy(closed, window)
