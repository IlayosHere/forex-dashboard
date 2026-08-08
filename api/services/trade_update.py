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
from api.services.trade_helpers import PnlInput, calculate_pnl, compute_risk_points

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
    "ict_cisd_present",
    "ict_htf_bias", "fees", "criteria_met_at_entry",
    "feeling_before", "feeling_during", "feeling_after",
    "be_outcome",
    "qt_fvg_quarter", "qt_entry_quarter", "qt_fvg_date",
    "qt_fvg_type", "qt_entry_type",
    "trade_location", "holding_time_minutes",
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

    _recalculate_risk_pips(trade, update_data)


def _recalculate_risk_pips(trade: TradeModel, update_data: dict[str, Any]) -> None:
    """Re-derive risk_pips from entry/SL whenever either one changes.

    entry_price and sl_price are independently editable after a trade is
    saved (e.g. correcting a wrong-direction entry). Without this, risk_pips
    stays frozen at its creation-time value and RR is computed against a
    risk distance that no longer matches the trade. An explicit risk_pips
    sent in the same request always wins.
    """
    if "risk_pips" in update_data:
        return
    if "entry_price" not in update_data and "sl_price" not in update_data:
        return
    trade.risk_pips = compute_risk_points(trade.entry_price, trade.sl_price)


def infer_outcome(pnl_pips: float) -> tuple[str, str]:
    """Return (outcome, status) inferred from P&L pips. Breakeven threshold: 0.1 pip."""
    if abs(pnl_pips) < _BREAKEVEN_THRESHOLD_PIPS:
        return "breakeven", "breakeven"
    if pnl_pips > 0:
        return "win", "closed"
    return "loss", "closed"


def _outcome_is_stale(outcome: str | None, pnl_pips: float) -> bool:
    """True if the stored outcome no longer matches the recomputed P&L sign."""
    expected, _ = infer_outcome(pnl_pips)
    return outcome != expected


def recalculate_pnl_on_close(trade: TradeModel, user_sent_outcome: bool, trade_id: str) -> None:
    """Recalculate P&L/RR whenever an exit price is present, and infer
    outcome/close_time when the trade is actually being closed.

    Runs regardless of status so that editing prices/direction on an open
    trade (or re-editing an already-closed one) always keeps P&L and RR in
    sync. Raises 422 if exit_price is missing while status is closed/breakeven.
    """
    closing = trade.status in ("closed", "breakeven")
    if closing and trade.exit_price is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="exit_price is required to close or mark a trade as breakeven",
        )
    if trade.exit_price is None:
        return
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
    if not closing:
        return
    if not user_sent_outcome and _outcome_is_stale(trade.outcome, pnl_pips):
        trade.outcome, trade.status = infer_outcome(pnl_pips)
    if trade.close_time is None:
        trade.close_time = datetime.now(timezone.utc)
    logger.info("Trade closed: %s pnl_pips=%s outcome=%s", trade_id, pnl_pips, trade.outcome)
