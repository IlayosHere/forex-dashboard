"""
api/routes/trades.py
--------------------
CRUD endpoints for the trade journal + aggregated stats.

POST   /api/trades         — create a new trade
GET    /api/trades          — list trades with filters
GET    /api/trades/stats    — aggregated performance stats
GET    /api/trades/{id}     — single trade
PUT    /api/trades/{id}     — update trade (close, edit notes, etc.)
DELETE /api/trades/{id}     — delete trade
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import SignalModel, TradeModel
from api.schemas import (
    TradeCreateRequest,
    TradeResponse,
    TradeStatsResponse,
    TradeUpdateRequest,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pip_size(symbol: str) -> float:
    return 0.01 if "JPY" in symbol.upper() else 0.0001


def _pip_value_per_lot(symbol: str, price: float) -> float:
    sym = symbol.upper()
    if sym.endswith("USD"):
        return 10.0
    if sym.startswith("USD"):
        pip = 0.01 if sym.endswith("JPY") else 0.0001
        return (100_000 * pip) / price
    return 10.0


def _calculate_pnl(
    symbol: str,
    direction: str,
    entry_price: float,
    exit_price: float,
    lot_size: float,
    risk_pips: float,
) -> tuple[float, float, float | None]:
    """Return (pnl_pips, pnl_usd, rr_achieved)."""
    direction_mult = 1.0 if direction == "BUY" else -1.0
    pip_size = _pip_size(symbol)
    pnl_pips = round((exit_price - entry_price) / pip_size * direction_mult, 1)
    pip_value = _pip_value_per_lot(symbol, entry_price)
    pnl_usd = round(pnl_pips * pip_value * lot_size, 2)
    rr_achieved = round(pnl_pips / risk_pips, 2) if risk_pips > 0 else None
    return pnl_pips, pnl_usd, rr_achieved


def _apply_filters(stmt, strategy, symbol, status, outcome, date_from, date_to):
    """Apply optional query filters to a SELECT statement."""
    if strategy is not None:
        stmt = stmt.where(TradeModel.strategy == strategy)
    if symbol is not None:
        stmt = stmt.where(TradeModel.symbol == symbol)
    if status is not None:
        stmt = stmt.where(TradeModel.status == status)
    if outcome is not None:
        stmt = stmt.where(TradeModel.outcome == outcome)
    if date_from is not None:
        stmt = stmt.where(TradeModel.open_time >= datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc))
    if date_to is not None:
        stmt = stmt.where(TradeModel.open_time <= datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc))
    return stmt


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/trades", response_model=TradeResponse, status_code=201)
def create_trade(
    req: TradeCreateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TradeModel:
    if req.signal_id is not None:
        signal = db.get(SignalModel, req.signal_id)
        if signal is None:
            raise HTTPException(status_code=404, detail="Linked signal not found")

    now = datetime.now(timezone.utc)
    trade = TradeModel(
        id=str(uuid.uuid4()),
        signal_id=req.signal_id,
        strategy=req.strategy,
        symbol=req.symbol,
        direction=req.direction,
        entry_price=req.entry_price,
        exit_price=None,
        sl_price=req.sl_price,
        tp_price=req.tp_price,
        lot_size=req.lot_size,
        status="open",
        outcome=None,
        pnl_pips=None,
        pnl_usd=None,
        rr_achieved=None,
        risk_pips=req.risk_pips,
        open_time=req.open_time,
        close_time=None,
        tags=req.tags,
        notes=req.notes,
        rating=req.rating,
        confidence=req.confidence,
        screenshot_url=req.screenshot_url,
        trade_metadata=req.metadata,
        created_at=now,
        updated_at=now,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


@router.get("/trades", response_model=list[TradeResponse])
def list_trades(
    db: Annotated[Session, Depends(get_db)],
    strategy: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    status: str | None = Query(default=None),
    outcome: str | None = Query(default=None),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TradeModel]:
    stmt = select(TradeModel).order_by(TradeModel.open_time.desc())
    stmt = _apply_filters(stmt, strategy, symbol, status, outcome, date_from, date_to)
    stmt = stmt.offset(offset).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/trades/stats", response_model=TradeStatsResponse)
def trade_stats(
    db: Annotated[Session, Depends(get_db)],
    strategy: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
) -> dict:
    stmt = select(TradeModel)
    stmt = _apply_filters(stmt, strategy, symbol, None, None, date_from, date_to)
    trades = list(db.scalars(stmt).all())

    total = len(trades)
    open_trades = sum(1 for t in trades if t.status == "open")
    closed = [t for t in trades if t.status in ("closed", "breakeven")]
    wins = sum(1 for t in closed if t.outcome == "win")
    losses = sum(1 for t in closed if t.outcome == "loss")
    breakevens = sum(1 for t in closed if t.outcome == "breakeven")

    win_rate = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else None

    rr_values = [t.rr_achieved for t in closed if t.rr_achieved is not None]
    avg_rr = round(sum(rr_values) / len(rr_values), 2) if rr_values else None

    pnl_pips_values = [t.pnl_pips for t in closed if t.pnl_pips is not None]
    total_pnl_pips = round(sum(pnl_pips_values), 1)

    pnl_usd_values = [t.pnl_usd for t in closed if t.pnl_usd is not None]
    total_pnl_usd = round(sum(pnl_usd_values), 2)

    best_trade_pnl = max(pnl_pips_values) if pnl_pips_values else None
    worst_trade_pnl = min(pnl_pips_values) if pnl_pips_values else None

    # Current streak: count consecutive same outcomes from most recent
    current_streak = 0
    sorted_closed = sorted(closed, key=lambda t: t.close_time or t.open_time, reverse=True)
    if sorted_closed:
        streak_outcome = sorted_closed[0].outcome
        for t in sorted_closed:
            if t.outcome == streak_outcome:
                current_streak += 1
            else:
                break
        if streak_outcome == "loss":
            current_streak = -current_streak

    # Profit factor
    gross_profit = sum(t.pnl_usd for t in closed if t.pnl_usd is not None and t.pnl_usd > 0)
    gross_loss = abs(sum(t.pnl_usd for t in closed if t.pnl_usd is not None and t.pnl_usd < 0))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else None

    # Average hold time
    hold_times = []
    for t in closed:
        if t.open_time and t.close_time:
            delta = t.close_time - t.open_time
            hold_times.append(delta.total_seconds() / 3600)
    avg_hold_time_hours = round(sum(hold_times) / len(hold_times), 1) if hold_times else None

    # Breakdown by strategy
    by_strategy: dict[str, dict] = {}
    for t in closed:
        s = t.strategy
        if s not in by_strategy:
            by_strategy[s] = {"total": 0, "wins": 0, "losses": 0, "win_rate": None, "total_pnl_pips": 0.0}
        by_strategy[s]["total"] += 1
        if t.outcome == "win":
            by_strategy[s]["wins"] += 1
        elif t.outcome == "loss":
            by_strategy[s]["losses"] += 1
        if t.pnl_pips is not None:
            by_strategy[s]["total_pnl_pips"] += t.pnl_pips
    for v in by_strategy.values():
        denom = v["wins"] + v["losses"]
        v["win_rate"] = round(v["wins"] / denom * 100, 1) if denom > 0 else None
        v["total_pnl_pips"] = round(v["total_pnl_pips"], 1)

    # Breakdown by symbol
    by_symbol: dict[str, dict] = {}
    for t in closed:
        s = t.symbol
        if s not in by_symbol:
            by_symbol[s] = {"total": 0, "wins": 0, "losses": 0, "win_rate": None, "total_pnl_pips": 0.0}
        by_symbol[s]["total"] += 1
        if t.outcome == "win":
            by_symbol[s]["wins"] += 1
        elif t.outcome == "loss":
            by_symbol[s]["losses"] += 1
        if t.pnl_pips is not None:
            by_symbol[s]["total_pnl_pips"] += t.pnl_pips
    for v in by_symbol.values():
        denom = v["wins"] + v["losses"]
        v["win_rate"] = round(v["wins"] / denom * 100, 1) if denom > 0 else None
        v["total_pnl_pips"] = round(v["total_pnl_pips"], 1)

    return {
        "total_trades": total,
        "open_trades": open_trades,
        "closed_trades": len(closed),
        "wins": wins,
        "losses": losses,
        "breakevens": breakevens,
        "win_rate": win_rate,
        "avg_rr": avg_rr,
        "total_pnl_pips": total_pnl_pips,
        "total_pnl_usd": total_pnl_usd,
        "best_trade_pnl": best_trade_pnl,
        "worst_trade_pnl": worst_trade_pnl,
        "current_streak": current_streak,
        "profit_factor": profit_factor,
        "avg_hold_time_hours": avg_hold_time_hours,
        "by_strategy": by_strategy,
        "by_symbol": by_symbol,
    }


@router.get("/trades/{trade_id}", response_model=TradeResponse)
def get_trade(
    trade_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> TradeModel:
    trade = db.get(TradeModel, trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade


@router.put("/trades/{trade_id}", response_model=TradeResponse)
def update_trade(
    trade_id: str,
    req: TradeUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TradeModel:
    trade = db.get(TradeModel, trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")

    update_data = req.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "metadata":
            setattr(trade, "trade_metadata", value)
        else:
            setattr(trade, field, value)

    # Auto-calculate P&L when closing with an exit price
    if trade.exit_price is not None and trade.status in ("closed", "breakeven"):
        pnl_pips, pnl_usd, rr_achieved = _calculate_pnl(
            symbol=trade.symbol,
            direction=trade.direction,
            entry_price=trade.entry_price,
            exit_price=trade.exit_price,
            lot_size=trade.lot_size,
            risk_pips=trade.risk_pips,
        )
        trade.pnl_pips = pnl_pips
        trade.pnl_usd = pnl_usd
        trade.rr_achieved = rr_achieved

    trade.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(trade)
    return trade


@router.delete("/trades/{trade_id}", status_code=204)
def delete_trade(
    trade_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    trade = db.get(TradeModel, trade_id)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    db.delete(trade)
    db.commit()
