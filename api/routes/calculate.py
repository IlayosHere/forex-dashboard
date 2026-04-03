"""
api/routes/calculate.py
-----------------------
POST /api/calculate — live lot-size recalculation when the user edits SL/TP.

Pure function, no database access. Delegates entirely to shared.calculator.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from api.schemas import CalculateRequest, CalculateResponse
from shared.calculator import calculate_lot_size

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/calculate", response_model=CalculateResponse)
def calculate(
    req: CalculateRequest,
    _user: Annotated[str, Depends(get_current_user)],
) -> CalculateResponse:
    """Calculate lot size from entry, SL, balance, and risk percent."""
    result = calculate_lot_size(
        symbol=req.symbol,
        entry=req.entry,
        sl_pips=req.sl_pips,
        account_balance=req.account_balance,
        risk_percent=req.risk_percent,
        tp_pips=req.tp_pips,
        instrument_type=req.instrument_type,
    )
    return CalculateResponse(**result)
