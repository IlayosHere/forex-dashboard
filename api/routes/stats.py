"""
api/routes/stats.py
-------------------
Extended statistics endpoints for the trade journal.

GET /api/trades/stats/equity-curve   - cumulative P&L over time
GET /api/trades/stats/daily-summary  - daily aggregated stats for heatmap
GET /api/trades/stats/ict            - ICT breakdown for MNQ futures trades
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import TradeModel
from api.schemas_stats import DailySummaryPoint, EquityCurvePoint, IctStatsResponse
from api.services.trade_filters import StatsFilterParams
from api.services.trade_helpers import apply_trade_filters
from api.services.trade_stats_extended import (
    build_daily_summary,
    build_equity_curve,
)
from api.services.trade_stats_ict import compute_ict_stats

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
    account_id: str | None = Query(default=None),
    from_date: str | None = Query(default=None, alias="from"),
    to_date: str | None = Query(default=None, alias="to"),
) -> dict:
    """Return ICT breakdown statistics for MNQ futures trades.

    Implicitly filters to instrument_type='futures_mnq'. Optional date filters
    use open_time; from/to accept ISO date strings (YYYY-MM-DD).
    """
    stmt = select(TradeModel).where(
        TradeModel.owner == current_user,
        TradeModel.instrument_type == "futures_mnq",
    )
    if account_id is not None:
        stmt = stmt.where(TradeModel.account_id == account_id)
    if from_date is not None:
        from_dt = datetime.combine(
            date.fromisoformat(from_date), datetime.min.time(), tzinfo=timezone.utc,
        )
        stmt = stmt.where(TradeModel.open_time >= from_dt)
    if to_date is not None:
        to_dt = datetime.combine(
            date.fromisoformat(to_date) + timedelta(days=1),
            datetime.min.time(),
            tzinfo=timezone.utc,
        )
        stmt = stmt.where(TradeModel.open_time < to_dt)
    trades = list(db.scalars(stmt).all())
    logger.debug("ict_stats: fetched %d MNQ trades for user %s", len(trades), current_user)
    return compute_ict_stats(trades)
