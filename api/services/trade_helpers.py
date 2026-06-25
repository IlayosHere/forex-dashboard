"""
api/services/trade_helpers.py
-----------------------------
Pure helper functions for trade P&L calculation and serialization.
Used exclusively by api/routes/trades.py.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from api.models import AccountModel, MistakeModel, TradeMistakeModel, TradeModel
from api.services.trade_filters import StatsFilterParams, TradeFilterParams
from shared.calculator import (
    futures_dollars_per_point,
    is_futures_symbol,
    pip_size,
    pip_value_per_lot,
)

logger = logging.getLogger(__name__)


def compute_risk_pips(
    entry_price: float, sl_price: float, symbol: str, instrument_type: str = "forex",
) -> float:
    """Derive risk in pips/points from entry and SL prices.

    Futures contracts report distance in points (not pips). Detection is
    symbol-first: MNQ, MES, etc. are recognised as futures. instrument_type
    starting with 'futures' is the fallback for older records.
    """
    distance = abs(entry_price - sl_price)
    if is_futures_symbol(symbol) or instrument_type.startswith("futures"):
        return round(distance, 2)
    return round(distance / pip_size(symbol), 1)


@dataclass(frozen=True)
class PnlInput:
    """Parameters needed to calculate trade P&L."""
    symbol: str
    direction: str
    entry_price: float
    exit_price: float
    lot_size: float
    risk_pips: float
    instrument_type: str = "forex"


def calculate_pnl(pnl: PnlInput) -> tuple[float, float, float | None]:
    """Return (pnl_pips, pnl_usd, rr_achieved).

    For futures, pnl_pips stores points and lot_size stores contracts.
    The dollar-per-point multiplier comes from the symbol (MNQ=$2, MES=$5),
    not from instrument_type. instrument_type is only used as a fallback for
    older trade records that may not have a recognised symbol.
    """
    direction_mult = 1.0 if pnl.direction == "BUY" else -1.0

    if is_futures_symbol(pnl.symbol) or pnl.instrument_type.startswith("futures"):
        dollars_per_point = futures_dollars_per_point(pnl.symbol) if is_futures_symbol(pnl.symbol) else 2.0
        pnl_points = round((pnl.exit_price - pnl.entry_price) * direction_mult, 2)
        pnl_usd = round(pnl_points * dollars_per_point * pnl.lot_size, 2)
        rr = round(pnl_points / pnl.risk_pips, 2) if pnl.risk_pips > 0 else None
        return pnl_points, pnl_usd, rr

    ps = pip_size(pnl.symbol)
    pnl_pips = round((pnl.exit_price - pnl.entry_price) / ps * direction_mult, 1)
    pip_val = pip_value_per_lot(pnl.symbol, pnl.entry_price)
    pnl_usd = round(pnl_pips * pip_val * pnl.lot_size, 2)
    rr = round(pnl_pips / pnl.risk_pips, 2) if pnl.risk_pips > 0 else None
    return pnl_pips, pnl_usd, rr


def apply_trade_filters(stmt: Select, filters: TradeFilterParams | StatsFilterParams) -> Select:
    """Apply optional query filters to a trade SELECT statement."""
    if filters.strategy is not None:
        stmt = stmt.where(TradeModel.strategy == filters.strategy)
    if filters.symbol is not None:
        stmt = stmt.where(TradeModel.symbol == filters.symbol)
    if getattr(filters, "status", None) is not None:
        stmt = stmt.where(TradeModel.status == filters.status)
    if getattr(filters, "outcome", None) is not None:
        stmt = stmt.where(TradeModel.outcome == filters.outcome)
    if filters.instrument_type is not None:
        if filters.instrument_type == "futures":
            # "futures" matches all futures trades: new canonical value + legacy values
            stmt = stmt.where(
                TradeModel.instrument_type.in_(("futures", "futures_mnq", "futures_mes")),
            )
        else:
            stmt = stmt.where(TradeModel.instrument_type == filters.instrument_type)
    rule_followed = getattr(filters, "rule_followed", None)
    if rule_followed is not None:
        stmt = stmt.where(TradeModel.rule_followed == rule_followed)
    if filters.account_id is not None:
        stmt = stmt.where(TradeModel.account_id == filters.account_id)
    filter_acct_type = getattr(filters, "account_type", None)
    if filter_acct_type is not None:
        stmt = stmt.join(
            AccountModel,
            TradeModel.account_id == AccountModel.id,
            isouter=True,
        ).where(AccountModel.account_type == filter_acct_type)
    exclude_acct_type = getattr(filters, "exclude_account_type", None)
    if exclude_acct_type is not None:
        stmt = stmt.join(
            AccountModel,
            TradeModel.account_id == AccountModel.id,
            isouter=True,
        ).where(
            (AccountModel.account_type != exclude_acct_type)
            | (AccountModel.id.is_(None)),
        )
    if filters.date_from is not None:
        stmt = stmt.where(
            TradeModel.open_time >= datetime.combine(
                filters.date_from, datetime.min.time(), tzinfo=timezone.utc,
            ),
        )
    if filters.date_to is not None:
        stmt = stmt.where(
            TradeModel.open_time <= datetime.combine(
                filters.date_to, datetime.max.time(), tzinfo=timezone.utc,
            ),
        )
    return stmt


def fetch_linked_mistakes(
    db: Session, trade_id: str,
) -> list[dict[str, str]]:
    """Return list of {id, name} dicts for all mistakes linked to a trade."""
    rows = list(db.scalars(
        select(TradeMistakeModel).where(TradeMistakeModel.trade_id == trade_id),
    ).all())
    if not rows:
        return []
    mistake_ids = [r.mistake_id for r in rows]
    mistakes = list(db.scalars(
        select(MistakeModel).where(MistakeModel.id.in_(mistake_ids)),
    ).all())
    return [{"id": m.id, "name": m.name} for m in mistakes]


def build_account_lookup(
    db: Session, trades: list[TradeModel],
) -> dict[str, AccountModel]:
    """Build account_id -> AccountModel lookup (avoids N+1)."""
    account_ids = {t.account_id for t in trades if t.account_id is not None}
    if not account_ids:
        return {}
    accounts = list(db.scalars(
        select(AccountModel).where(AccountModel.id.in_(account_ids)),
    ).all())
    return {a.id: a for a in accounts}


def trade_to_response(
    trade: TradeModel,
    account_lookup: dict[str, AccountModel],
    db: Session | None = None,
) -> dict[str, Any]:
    """Convert TradeModel to a dict for TradeResponse serialization."""
    account = account_lookup.get(trade.account_id) if trade.account_id else None
    linked_mistakes = fetch_linked_mistakes(db, trade.id) if db is not None else []
    return {
        "id": trade.id,
        "signal_id": trade.signal_id,
        "scenario_id": trade.scenario_id,
        "account_id": trade.account_id,
        "account_name": account.name if account else None,
        "strategy": trade.strategy,
        "symbol": trade.symbol,
        "instrument_type": trade.instrument_type,
        "direction": trade.direction,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "sl_price": trade.sl_price,
        "tp_price": trade.tp_price,
        "lot_size": trade.lot_size,
        "status": trade.status,
        "outcome": trade.outcome,
        "pnl_pips": trade.pnl_pips,
        "pnl_usd": trade.pnl_usd,
        "rr_achieved": trade.rr_achieved,
        "risk_pips": trade.risk_pips,
        "open_time": trade.open_time,
        "close_time": trade.close_time,
        "tags": trade.tags,
        "notes": trade.notes,
        "rating": trade.rating,
        "confidence": trade.confidence,
        "rule_followed": trade.rule_followed,
        "linked_mistakes": linked_mistakes,
        "screenshot_url": trade.screenshot_url,
        "trade_metadata": trade.trade_metadata,
        "ict_setup_type": trade.ict_setup_type,
        "ict_setup_detail": trade.ict_setup_detail,
        "ict_tp_target": trade.ict_tp_target,
        "ict_ifvg_timeframe": trade.ict_ifvg_timeframe,
        "ict_ifvg_bars": trade.ict_ifvg_bars,
        "ict_smt_present": trade.ict_smt_present,
        "ict_tdo_aligned": trade.ict_tdo_aligned,
        "ict_cisd_present": trade.ict_cisd_present,
        "ict_htf_bias": trade.ict_htf_bias,
        "fees": trade.fees,
        "criteria_met_at_entry": trade.criteria_met_at_entry,
        "feeling_before": trade.feeling_before,
        "feeling_during": trade.feeling_during,
        "feeling_after": trade.feeling_after,
        "be_outcome": trade.be_outcome,
        "qt_fvg_quarter": trade.qt_fvg_quarter,
        "qt_entry_quarter": trade.qt_entry_quarter,
        "qt_fvg_date": trade.qt_fvg_date,
        "qt_fvg_type": trade.qt_fvg_type,
        "qt_entry_type": trade.qt_entry_type,
        "created_at": trade.created_at,
        "updated_at": trade.updated_at,
    }
