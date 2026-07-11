"""
api/routes/trades.py
--------------------
CRUD endpoints for the trade journal + aggregated stats.

POST   /api/trades         - create a new trade
GET    /api/trades          - list trades with filters
GET    /api/trades/stats    - aggregated performance stats
GET    /api/trades/{id}     - single trade
PUT    /api/trades/{id}     - update trade (close, edit notes, etc.)
DELETE /api/trades/{id}     - delete trade
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import AccountModel, TradeModel
from api.schemas import (
    DayTypeResponse,
    TradeCreateRequest,
    TradeResponse,
    TradeStatsResponse,
    TradeUpdateRequest,
)
from api.services.trade_filters import StatsFilterParams, TradeFilterParams
from api.services.trade_helpers import (
    apply_trade_filters,
    build_account_lookup,
    compute_risk_points,
    trade_to_response,
)
from api.services.trade_update import (
    apply_update_fields,
    guard_terminal_status,
    recalculate_pnl_on_close,
)
from api.services.trade_stats import (
    aggregate_by_account,
    aggregate_by_field,
    calculate_trade_metrics,
)
from api.services.trade_stats_extended import (
    aggregate_be_outcome,
    aggregate_by_assessment,
    aggregate_by_criteria_met,
    aggregate_by_day_of_week,
    aggregate_by_feeling_before,
    aggregate_by_location,
    aggregate_by_rule_compliance,
    aggregate_by_session,
    calculate_edge_metrics,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/trades", response_model=TradeResponse, status_code=201)
def create_trade(
    req: TradeCreateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Create a new trade journal entry."""
    if req.account_id is not None:
        acct = db.get(AccountModel, req.account_id)
        if acct is None or acct.owner != current_user:
            logger.warning("Linked account not found: %s", req.account_id)
            raise HTTPException(status_code=404, detail="Linked account not found")

    risk_pips = req.risk_pips if req.risk_pips is not None else compute_risk_points(
        req.entry_price, req.sl_price,
    )

    now = datetime.now(timezone.utc)
    trade = TradeModel(
        id=str(uuid.uuid4()), signal_id=req.signal_id, scenario_id=req.scenario_id,
        account_id=req.account_id, strategy=req.strategy,
        owner=current_user,
        symbol=req.symbol, instrument_type=req.instrument_type,
        direction=req.direction, entry_price=req.entry_price,
        exit_price=None, sl_price=req.sl_price, tp_price=req.tp_price,
        lot_size=req.lot_size, status="open", outcome=None,
        pnl_pips=None, pnl_usd=None, rr_achieved=None,
        risk_pips=risk_pips, open_time=req.open_time, close_time=None,
        tags=req.tags, notes=req.notes, rating=req.rating,
        confidence=req.confidence, screenshot_url=req.screenshot_url,
        trade_metadata=req.metadata, created_at=now, updated_at=now,
        ict_setup_type=req.ict_setup_type,
        ict_setup_detail=req.ict_setup_detail,
        ict_tp_target=req.ict_tp_target,
        ict_ifvg_timeframe=req.ict_ifvg_timeframe,
        ict_ifvg_bars=req.ict_ifvg_bars,
        ict_smt_present=req.ict_smt_present,
        ict_tdo_aligned=req.ict_tdo_aligned,
        ict_cisd_present=req.ict_cisd_present,
        ict_htf_bias=req.ict_htf_bias,
        fees=req.fees,
        criteria_met_at_entry=req.criteria_met_at_entry,
        feeling_before=req.feeling_before,
        feeling_during=req.feeling_during,
        feeling_after=req.feeling_after,
        be_outcome=req.be_outcome,
        qt_fvg_quarter=req.qt_fvg_quarter,
        qt_entry_quarter=req.qt_entry_quarter,
        qt_fvg_date=req.qt_fvg_date,
        qt_fvg_type=req.qt_fvg_type,
        qt_entry_type=req.qt_entry_type,
        trade_location=req.trade_location,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    logger.info("Trade created: %s %s %s", trade.id, trade.symbol, trade.direction)
    return trade_to_response(trade, build_account_lookup(db, [trade]), db)


@router.get("/trades", response_model=list[TradeResponse])
def list_trades(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[TradeFilterParams, Depends()],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    """List trades with optional filters, newest first."""
    stmt = select(TradeModel).order_by(TradeModel.open_time.desc())
    stmt = stmt.where(TradeModel.owner == current_user)
    stmt = apply_trade_filters(stmt, filters)
    if filters.status is None:
        stmt = stmt.where(TradeModel.status != "cancelled")
    stmt = stmt.offset(offset).limit(limit)
    trades = list(db.scalars(stmt).all())
    lookup = build_account_lookup(db, trades)
    return [trade_to_response(t, lookup, db) for t in trades]


@router.get("/trades/stats", response_model=TradeStatsResponse)
def trade_stats(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[StatsFilterParams, Depends()],
) -> dict[str, Any]:
    """Return aggregated performance statistics for filtered trades."""
    stmt = select(TradeModel)
    stmt = stmt.where(TradeModel.owner == current_user)
    stmt = apply_trade_filters(stmt, filters)
    stmt = stmt.where(TradeModel.status != "cancelled")
    trades = list(db.scalars(stmt).all())
    closed = [t for t in trades if t.status in ("closed", "breakeven")]

    metrics = calculate_trade_metrics(trades, closed)
    metrics["by_strategy"] = aggregate_by_field(closed, "strategy")
    metrics["by_symbol"] = aggregate_by_field(closed, "symbol")
    metrics["by_account"] = aggregate_by_account(
        closed, build_account_lookup(db, trades),
    )
    metrics.update(calculate_edge_metrics(closed))
    metrics["by_day_of_week"] = aggregate_by_day_of_week(closed)
    metrics["by_session"] = aggregate_by_session(closed)
    metrics["by_confidence"] = aggregate_by_assessment(closed, "confidence")
    metrics["by_rating"] = aggregate_by_assessment(closed, "rating")
    metrics["by_rule_compliance"] = aggregate_by_rule_compliance(closed)
    metrics["by_criteria_met"] = aggregate_by_criteria_met(closed)
    metrics["be_outcome_breakdown"] = aggregate_be_outcome(closed)
    metrics["by_location"] = aggregate_by_location(closed)
    metrics["by_feeling_before"] = aggregate_by_feeling_before(closed)
    metrics.update(_news_and_holiday_breakdowns(closed))
    from api.services.trade_stats_extended import build_equity_curve
    from api.services.trade_stats_live import compute_drawdown, compute_tp_capture
    from api.services.trade_stats_robustness import compute_r_distribution
    curve = build_equity_curve(closed)
    metrics["live_drawdown"] = compute_drawdown(curve)
    metrics.update(compute_tp_capture(closed))
    metrics["r_distribution"] = compute_r_distribution(closed)
    if filters.account_type == "backtest":
        from api.services.trade_stats_robustness import (
            compute_drawdown_stats,
            compute_edge_robustness,
            compute_expectancy_ci,
        )
        r_values = [
            t.rr_achieved
            for t in closed
            if t.rr_achieved is not None and t.outcome in ("win", "loss")
        ]
        metrics["drawdown"] = compute_drawdown_stats(curve, closed)
        metrics["robustness"] = compute_edge_robustness(closed)
        metrics["expectancy_ci"] = compute_expectancy_ci(r_values)
    return metrics


def _news_and_holiday_breakdowns(closed: list[TradeModel]) -> dict[str, Any]:
    """by_news_day / by_market_holiday breakdowns — computed for every account
    type. The trade data itself is what's scarce for live accounts, not the
    lookup. Also reports the underlying hand-maintained tables' coverage
    limit so the frontend can flag trades beyond it rather than silently
    imply "confirmed no news"."""
    from shared.economic_calendar import coverage_through as news_coverage_through
    from shared.market_holidays import cme_coverage_through

    from api.services.trade_stats_news import (
        aggregate_by_market_holiday,
        aggregate_by_news_day,
        build_holiday_day_map,
        build_news_day_map,
    )

    coverage = {
        "news_data_coverage_through": news_coverage_through().isoformat(),
        "holiday_data_coverage_through": cme_coverage_through().isoformat(),
    }
    open_dates = [t.open_time.date() for t in closed if t.open_time]
    if not open_dates:
        return {"by_news_day": {}, "by_market_holiday": {}, **coverage}
    start, end = min(open_dates), max(open_dates)
    return {
        "by_news_day": aggregate_by_news_day(closed, build_news_day_map(start, end)),
        "by_market_holiday": aggregate_by_market_holiday(closed, build_holiday_day_map(start, end)),
        **coverage,
    }


@router.get("/trades/day-types", response_model=list[DayTypeResponse])
def list_day_types(
    _: Annotated[str, Depends(get_current_user)],
    date_from: Annotated[date, Query(alias="from")],
    date_to: Annotated[date, Query(alias="to")],
) -> list[dict[str, Any]]:
    """Per-day news/holiday info for the backtest journal calendar.

    news_impact/market_status are collapsed flags for the grid's day-cell dot;
    news_events/holiday_events carry the full entries for the day-sheet detail
    view (a day can have more than one news event or holiday entry).
    """
    from api.services.trade_stats_news import (
        build_holiday_day_map,
        build_news_day_map,
        holiday_events_by_date,
        news_events_by_date,
    )

    news_days = build_news_day_map(date_from, date_to)
    holiday_days = build_holiday_day_map(date_from, date_to)
    news_events = news_events_by_date(date_from, date_to)
    holiday_events = holiday_events_by_date(date_from, date_to)
    days = {*news_days.keys(), *holiday_days.keys()}
    return [
        {
            "date": d.isoformat(),
            "news_impact": news_days.get(d),
            "market_status": holiday_days.get(d),
            "news_events": news_events.get(d, []),
            "holiday_events": holiday_events.get(d, []),
        }
        for d in sorted(days)
    ]


@router.get("/trades/{trade_id}", response_model=TradeResponse)
def get_trade(
    trade_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Fetch a single trade by ID, return 404 if not found."""
    trade = db.get(TradeModel, trade_id)
    if trade is None or trade.owner != current_user:
        logger.warning("Trade not found: %s", trade_id)
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade_to_response(trade, build_account_lookup(db, [trade]), db)


@router.put("/trades/{trade_id}", response_model=TradeResponse)
def update_trade(
    trade_id: str,
    req: TradeUpdateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Update a trade (close it, edit notes, tags, etc.)."""
    trade = db.get(TradeModel, trade_id)
    if trade is None or trade.owner != current_user:
        logger.warning("Trade not found for update: %s", trade_id)
        raise HTTPException(status_code=404, detail="Trade not found")

    update_data = req.model_dump(exclude_unset=True)
    user_sent_outcome = "outcome" in update_data
    guard_terminal_status(trade, update_data.get("status", trade.status))
    apply_update_fields(trade, update_data)
    recalculate_pnl_on_close(trade, user_sent_outcome, trade_id)

    trade.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(trade)
    return trade_to_response(trade, build_account_lookup(db, [trade]), db)


@router.delete("/trades/{trade_id}", status_code=204)
def delete_trade(
    trade_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a trade by ID, return 404 if not found."""
    trade = db.get(TradeModel, trade_id)
    if trade is None or trade.owner != current_user:
        logger.warning("Trade not found for deletion: %s", trade_id)
        raise HTTPException(status_code=404, detail="Trade not found")
    db.delete(trade)
    db.commit()
    logger.info("Trade deleted: %s", trade_id)
