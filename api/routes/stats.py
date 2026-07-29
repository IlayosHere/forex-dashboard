"""
api/routes/stats.py
-------------------
Extended statistics endpoints for the trade journal.

GET /api/trades/stats/equity-curve   - cumulative P&L over time
GET /api/trades/stats/daily-summary  - daily aggregated stats for heatmap
GET /api/trades/stats/ict            - ICT breakdown for MNQ futures trades
GET /api/trades/stats/rolling-pf     - rolling profit factor (backtest mode)
GET /api/trades/stats/mistakes/timeseries - mistake counts bucketed weekly/monthly
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import MistakeModel, TradeMistakeModel, TradeModel
from api.schemas_stats import (
    DailySummaryPoint,
    EquityCurvePoint,
    IctStatsResponse,
    MistakePeriodBucket,
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
from api.services.trade_stats_mistakes import aggregate_mistakes, build_mistake_timeseries
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


def _fetch_mistake_links(
    db: Session,
    trade_ids: set[str],
) -> tuple[list[TradeMistakeModel], dict[str, str]]:
    """Fetch mistake links for the given trade ids plus their id->name map."""
    if not trade_ids:
        return [], {}
    links = list(db.scalars(
        select(TradeMistakeModel).where(TradeMistakeModel.trade_id.in_(trade_ids)),
    ).all())
    if not links:
        return [], {}
    mistake_ids = {lnk.mistake_id for lnk in links}
    mistakes = list(db.scalars(
        select(MistakeModel).where(MistakeModel.id.in_(mistake_ids)),
    ).all())
    return links, {m.id: m.name for m in mistakes}


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
    closed = _fetch_closed_trades(current_user, db, filters)
    closed_ids = {t.id for t in closed}
    links, name_map = _fetch_mistake_links(db, closed_ids)
    if not links:
        return []
    trade_map = {t.id: t for t in closed}
    return aggregate_mistakes(trade_map, links, name_map)


@router.get(
    "/trades/stats/mistakes/timeseries",
    response_model=list[MistakePeriodBucket],
)
def mistake_timeseries(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[StatsFilterParams, Depends()],
    granularity: str = Query(default="week", pattern="^(week|month)$"),
) -> list[dict]:
    """Return per-mistake stats bucketed into weekly or monthly periods.

    Only live-mode trades (non-backtest), same filters as /stats/mistakes.
    Lets a trader compare "how often did I make mistake X" period over period.
    """
    closed = _fetch_closed_trades(current_user, db, filters)
    closed_ids = {t.id for t in closed}
    links, name_map = _fetch_mistake_links(db, closed_ids)
    try:
        return build_mistake_timeseries(closed, links, name_map, granularity)
    except ValueError as exc:
        logger.warning("mistake_timeseries: invalid granularity=%s", granularity)
        raise HTTPException(status_code=422, detail=str(exc)) from exc


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
