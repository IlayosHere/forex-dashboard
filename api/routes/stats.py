"""
api/routes/stats.py
-------------------
Extended statistics endpoints for the trade journal.

GET /api/trades/stats/equity-curve   - cumulative P&L over time
GET /api/trades/stats/daily-summary  - daily aggregated stats for heatmap
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import TradeModel
from api.schemas_stats import DailySummaryPoint, EquityCurvePoint
from api.services.trade_helpers import apply_trade_filters
from api.services.trade_stats_extended import (
    build_daily_summary,
    build_equity_curve,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class _StatsFilterParams:
    """Dependency for stats filter query parameters."""

    def __init__(
        self,
        strategy: str | None = Query(default=None),
        symbol: str | None = Query(default=None),
        instrument_type: str | None = Query(default=None),
        account_id: str | None = Query(default=None),
        date_from: date | None = Query(default=None, alias="from"),
        date_to: date | None = Query(default=None, alias="to"),
    ) -> None:
        self.strategy = strategy
        self.symbol = symbol
        self.instrument_type = instrument_type
        self.account_id = account_id
        self.date_from = date_from
        self.date_to = date_to


def _fetch_closed_trades(
    current_user: str,
    db: Session,
    filters: _StatsFilterParams,
) -> list[TradeModel]:
    """Query closed/breakeven trades with filters applied."""
    stmt = select(TradeModel).where(TradeModel.owner == current_user)
    stmt = apply_trade_filters(
        stmt, filters.strategy, filters.symbol, None, None,
        filters.date_from, filters.date_to,
        filters.instrument_type, filters.account_id,
    )
    stmt = stmt.where(TradeModel.status.in_(("closed", "breakeven")))
    return list(db.scalars(stmt).all())


@router.get(
    "/trades/stats/equity-curve",
    response_model=list[EquityCurvePoint],
)
def equity_curve(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[_StatsFilterParams, Depends()],
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
    filters: Annotated[_StatsFilterParams, Depends()],
) -> list[dict]:
    """Return daily aggregated stats for calendar heatmap."""
    closed = _fetch_closed_trades(current_user, db, filters)
    return build_daily_summary(closed)
