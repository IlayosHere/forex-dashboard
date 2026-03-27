"""
api/routes/calculate.py
-----------------------
POST /api/calculate — live lot-size recalculation when the user edits SL/TP.

Pure function, no database access. Delegates entirely to shared.calculator.
"""
from __future__ import annotations

from fastapi import APIRouter

from api.schemas import CalculateRequest, CalculateResponse
from shared.calculator import calculate_lot_size

router = APIRouter()


@router.post("/calculate", response_model=CalculateResponse)
def calculate(req: CalculateRequest) -> CalculateResponse:
    result = calculate_lot_size(
        symbol=req.symbol,
        entry=req.entry,
        sl_pips=req.sl_pips,
        account_balance=req.account_balance,
        risk_percent=req.risk_percent,
        tp_pips=req.tp_pips,
    )
    return CalculateResponse(**result)
