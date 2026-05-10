"""
api/services/trade_update.py
-----------------------------
Business logic for the PUT /api/trades/{id} endpoint.

Extracted from api/routes/trades.py to keep the route handler under the
40-line limit. All functions are pure (no DB commits) — the route handler
owns the session lifecycle.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from api.models import TradeModel
from api.services.trade_helpers import PnlInput, calculate_pnl

logger = logging.getLogger(__name__)

_BREAKEVEN_THRESHOLD_PIPS: float = 0.1
_TERMINAL: frozenset[str] = frozenset({"closed", "breakeven", "cancelled"})

_ALLOWED_UPDATE_FIELDS: frozenset[str] = frozenset({
    "instrument_type", "direction", "entry_price", "exit_price",
    "sl_price", "tp_price", "lot_size", "risk_pips", "status",
    "outcome", "open_time", "close_time", "tags", "notes", "rating",
    "confidence", "rule_followed", "screenshot_url", "metadata",
    "ict_setup_type", "ict_setup_detail", "ict_tp_target",
    "ict_ifvg_timeframe", "ict_ifvg_bars", "ict_smt_present", "ict_tdo_aligned",
    "ict_htf_bias", "fees", "criteria_met_at_entry",
    "feeling_before", "feeling_during", "feeling_after",
    "be_outcome",
})


def guard_terminal_status(trade: TradeModel, new_status: str) -> None:
    """Raise 422 if the trade is terminal and new_status would reopen it."""
    if trade.status in _TERMINAL and new_status not in _TERMINAL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot change status from '{trade.status}' to '{new_status}'",
        )


def apply_update_fields(trade: TradeModel, update_data: dict[str, Any]) -> None:
    """Apply allowed fields from update_data onto the trade model in-place.

    Special case: if status is being set to "cancelled", exit_price is forced
    to None. A cancelled trade has no exit, so storing an exit_price would
    create a data inconsistency (PnL is never computed for cancelled status).
    """
    for field, value in update_data.items():
        if field not in _ALLOWED_UPDATE_FIELDS:
            continue
        if field == "metadata":
            setattr(trade, "trade_metadata", value)
        else:
            setattr(trade, field, value)

    if update_data.get("status") == "cancelled":
        trade.exit_price = None


def infer_outcome(pnl_pips: float) -> tuple[str, str]:
    """Return (outcome, status) inferred from P&L pips. Breakeven threshold: 0.1 pip."""
    if abs(pnl_pips) < _BREAKEVEN_THRESHOLD_PIPS:
        return "breakeven", "breakeven"
    if pnl_pips > 0:
        return "win", "closed"
    return "loss", "closed"


def recalculate_pnl_on_close(trade: TradeModel, user_sent_outcome: bool, trade_id: str) -> None:
    """Recalculate P&L and infer outcome when closing a trade.

    Mutates trade in-place. Raises 422 if exit_price is missing.
    """
    if trade.status not in ("closed", "breakeven"):
        return
    if trade.exit_price is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="exit_price is required to close or mark a trade as breakeven",
        )
    pnl_pips, pnl_usd, rr = calculate_pnl(PnlInput(
        symbol=trade.symbol, direction=trade.direction,
        entry_price=trade.entry_price, exit_price=trade.exit_price,
        lot_size=trade.lot_size, risk_pips=trade.risk_pips,
        instrument_type=trade.instrument_type,
    ))
    if trade.fees:
        pnl_usd = round(pnl_usd - trade.fees, 2)
    trade.pnl_pips = pnl_pips
    trade.pnl_usd = pnl_usd
    trade.rr_achieved = rr
    if not user_sent_outcome and trade.outcome is None:
        trade.outcome, trade.status = infer_outcome(pnl_pips)
    if trade.close_time is None:
        trade.close_time = datetime.now(timezone.utc)
    logger.info("Trade closed: %s pnl_pips=%s outcome=%s", trade_id, pnl_pips, trade.outcome)
