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
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import AccountModel, SignalModel, TradeModel
from api.schemas import (
    TradeCreateRequest,
    TradeResponse,
    TradeStatsResponse,
    TradeUpdateRequest,
)
from api.services.trade_helpers import (
    PnlInput,
    apply_trade_filters,
    build_account_lookup,
    calculate_pnl,
    trade_to_response,
)
from api.services.trade_stats import (
    aggregate_by_account,
    aggregate_by_field,
    calculate_trade_metrics,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Query filter dependency — groups filter params for list_trades / trade_stats
# ---------------------------------------------------------------------------


class _TradeFilterParams:
    """Dependency that collects trade filter query parameters."""

    def __init__(
        self,
        strategy: str | None = Query(default=None),
        symbol: str | None = Query(default=None),
        status: str | None = Query(default=None),
        outcome: str | None = Query(default=None),
        instrument_type: str | None = Query(default=None),
        account_id: str | None = Query(default=None),
        date_from: date | None = Query(default=None, alias="from"),
        date_to: date | None = Query(default=None, alias="to"),
    ) -> None:
        self.strategy = strategy
        self.symbol = symbol
        self.status = status
        self.outcome = outcome
        self.instrument_type = instrument_type
        self.account_id = account_id
        self.date_from = date_from
        self.date_to = date_to


@router.post("/trades", response_model=TradeResponse, status_code=201)
def create_trade(
    req: TradeCreateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Create a new trade journal entry."""
    if req.signal_id is not None:
        if db.get(SignalModel, req.signal_id) is None:
            logger.warning("Linked signal not found: %s", req.signal_id)
            raise HTTPException(status_code=404, detail="Linked signal not found")
    if req.account_id is not None:
        if db.get(AccountModel, req.account_id) is None:
            logger.warning("Linked account not found: %s", req.account_id)
            raise HTTPException(status_code=404, detail="Linked account not found")

    now = datetime.now(timezone.utc)
    trade = TradeModel(
        id=str(uuid.uuid4()), signal_id=req.signal_id,
        account_id=req.account_id, strategy=req.strategy,
        symbol=req.symbol, instrument_type=req.instrument_type,
        direction=req.direction, entry_price=req.entry_price,
        exit_price=None, sl_price=req.sl_price, tp_price=req.tp_price,
        lot_size=req.lot_size, status="open", outcome=None,
        pnl_pips=None, pnl_usd=None, rr_achieved=None,
        risk_pips=req.risk_pips, open_time=req.open_time, close_time=None,
        tags=req.tags, notes=req.notes, rating=req.rating,
        confidence=req.confidence, screenshot_url=req.screenshot_url,
        trade_metadata=req.metadata, created_at=now, updated_at=now,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    logger.info("Trade created: %s %s %s", trade.id, trade.symbol, trade.direction)
    return trade_to_response(trade, build_account_lookup(db, [trade]))


@router.get("/trades", response_model=list[TradeResponse])
def list_trades(
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[_TradeFilterParams, Depends()],
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    """List trades with optional filters, newest first."""
    stmt = select(TradeModel).order_by(TradeModel.open_time.desc())
    stmt = apply_trade_filters(
        stmt, filters.strategy, filters.symbol, filters.status,
        filters.outcome, filters.date_from, filters.date_to,
        filters.instrument_type, filters.account_id,
    )
    if filters.status is None:
        stmt = stmt.where(TradeModel.status != "cancelled")
    stmt = stmt.offset(offset).limit(limit)
    trades = list(db.scalars(stmt).all())
    lookup = build_account_lookup(db, trades)
    return [trade_to_response(t, lookup) for t in trades]


@router.get("/trades/stats", response_model=TradeStatsResponse)
def trade_stats(
    db: Annotated[Session, Depends(get_db)],
    filters: Annotated[_TradeFilterParams, Depends()],
) -> dict:
    """Return aggregated performance statistics for filtered trades."""
    stmt = select(TradeModel)
    stmt = apply_trade_filters(
        stmt, filters.strategy, filters.symbol, None, None,
        filters.date_from, filters.date_to,
        filters.instrument_type, filters.account_id,
    )
    stmt = stmt.where(TradeModel.status != "cancelled")
    trades = list(db.scalars(stmt).all())
    closed = [t for t in trades if t.status in ("closed", "breakeven")]

    metrics = calculate_trade_metrics(trades, closed)
    metrics["by_strategy"] = aggregate_by_field(closed, "strategy")
    metrics["by_symbol"] = aggregate_by_field(closed, "symbol")
    metrics["by_account"] = aggregate_by_account(
        closed, build_account_lookup(db, trades),
    )
    return metrics


@router.get("/trades/{trade_id}", response_model=TradeResponse)
def get_trade(
    trade_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Fetch a single trade by ID, return 404 if not found."""
    trade = db.get(TradeModel, trade_id)
    if trade is None:
        logger.warning("Trade not found: %s", trade_id)
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade_to_response(trade, build_account_lookup(db, [trade]))


@router.put("/trades/{trade_id}", response_model=TradeResponse)
def update_trade(
    trade_id: str,
    req: TradeUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """Update a trade (close it, edit notes, tags, etc.)."""
    trade = db.get(TradeModel, trade_id)
    if trade is None:
        logger.warning("Trade not found for update: %s", trade_id)
        raise HTTPException(status_code=404, detail="Trade not found")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "metadata":
            setattr(trade, "trade_metadata", value)
        else:
            setattr(trade, field, value)

    if trade.exit_price is not None and trade.status in ("closed", "breakeven"):
        pnl_pips, pnl_usd, rr = calculate_pnl(PnlInput(
            symbol=trade.symbol, direction=trade.direction,
            entry_price=trade.entry_price, exit_price=trade.exit_price,
            lot_size=trade.lot_size, risk_pips=trade.risk_pips,
            instrument_type=trade.instrument_type,
        ))
        trade.pnl_pips = pnl_pips
        trade.pnl_usd = pnl_usd
        trade.rr_achieved = rr
        logger.info("Trade closed: %s pnl_pips=%s", trade_id, pnl_pips)

    trade.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(trade)
    return trade_to_response(trade, build_account_lookup(db, [trade]))


@router.delete("/trades/{trade_id}", status_code=204)
def delete_trade(
    trade_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a trade by ID, return 404 if not found."""
    trade = db.get(TradeModel, trade_id)
    if trade is None:
        logger.warning("Trade not found for deletion: %s", trade_id)
        raise HTTPException(status_code=404, detail="Trade not found")
    db.delete(trade)
    db.commit()
    logger.info("Trade deleted: %s", trade_id)
