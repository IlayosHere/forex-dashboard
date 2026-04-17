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
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models import AccountModel, SignalModel, TradeModel
from api.schemas import (
    TradeCreateRequest,
    TradeResponse,
    TradeStatsResponse,
    TradeUpdateRequest,
)
from api.services.trade_filters import StatsFilterParams, TradeFilterParams
from api.services.trade_helpers import (
    apply_trade_filters,
    build_account_lookup,
    compute_risk_pips,
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
    aggregate_by_assessment,
    aggregate_by_day_of_week,
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
    if req.signal_id is not None:
        if db.get(SignalModel, req.signal_id) is None:
            logger.warning("Linked signal not found: %s", req.signal_id)
            raise HTTPException(status_code=404, detail="Linked signal not found")
    if req.account_id is not None:
        acct = db.get(AccountModel, req.account_id)
        if acct is None or acct.owner != current_user:
            logger.warning("Linked account not found: %s", req.account_id)
            raise HTTPException(status_code=404, detail="Linked account not found")

    risk_pips = req.risk_pips if req.risk_pips is not None else compute_risk_pips(
        req.entry_price, req.sl_price, req.symbol, req.instrument_type,
    )

    now = datetime.now(timezone.utc)
    trade = TradeModel(
        id=str(uuid.uuid4()), signal_id=req.signal_id,
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
        ict_smt_present=req.ict_smt_present,
        ict_tdo_aligned=req.ict_tdo_aligned,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    logger.info("Trade created: %s %s %s", trade.id, trade.symbol, trade.direction)
    return trade_to_response(trade, build_account_lookup(db, [trade]))


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
    return [trade_to_response(t, lookup) for t in trades]


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
    return metrics


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
    return trade_to_response(trade, build_account_lookup(db, [trade]))


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
    return trade_to_response(trade, build_account_lookup(db, [trade]))


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
