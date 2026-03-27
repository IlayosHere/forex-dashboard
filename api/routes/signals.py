"""
api/routes/signals.py
---------------------
GET /api/signals   — list signals with optional filters, newest first
GET /api/signals/{id} — single signal by primary key
"""
from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.db import get_db
from api.models import SignalModel
from api.schemas import SignalResponse, SignalListResponse

router = APIRouter()


@router.get("/signals", response_model=SignalListResponse)
def list_signals(
    db: Annotated[Session, Depends(get_db)],
    strategy: str | None = Query(default=None, description="Filter by strategy slug"),
    symbol: str | None = Query(default=None, description="Filter by currency pair"),
    direction: str | None = Query(default=None, description="Filter by BUY or SELL"),
    date_from: datetime | None = Query(default=None, alias="from", description="Start date (inclusive)"),
    date_to: datetime | None = Query(default=None, alias="to", description="End date (inclusive)"),
    limit: int = Query(default=50, ge=1, le=200, description="Max results (1–200)"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> dict:
    base = select(SignalModel)
    if strategy is not None:
        base = base.where(SignalModel.strategy == strategy)
    if symbol is not None:
        base = base.where(SignalModel.symbol == symbol)
    if direction is not None:
        base = base.where(SignalModel.direction == direction)
    if date_from is not None:
        base = base.where(SignalModel.candle_time >= date_from)
    if date_to is not None:
        base = base.where(SignalModel.candle_time <= date_to)

    total = db.scalar(select(func.count()).select_from(base.subquery()))
    items = list(
        db.scalars(
            base.order_by(SignalModel.candle_time.desc()).offset(offset).limit(limit)
        ).all()
    )
    return {"items": items, "total": total or 0}


@router.get("/signals/{signal_id}", response_model=SignalResponse)
def get_signal(
    signal_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> SignalModel:
    signal = db.get(SignalModel, signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal
