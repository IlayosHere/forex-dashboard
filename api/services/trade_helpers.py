"""
api/services/trade_helpers.py
-----------------------------
Pure helper functions for trade P&L calculation and serialization.
Used exclusively by api/routes/trades.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from api.models import AccountModel, TradeModel
from shared.calculator import pip_size, pip_value_per_lot


def compute_risk_pips(
    entry_price: float, sl_price: float, symbol: str, instrument_type: str = "forex",
) -> float:
    """Derive risk in pips/points from entry and SL prices."""
    distance = abs(entry_price - sl_price)
    if instrument_type == "futures_mnq":
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

    For futures_mnq, pnl_pips stores points and lot_size stores contracts.
    MNQ tick value is $0.50 per 0.25 point = $2.00 per point per contract.
    """
    direction_mult = 1.0 if pnl.direction == "BUY" else -1.0

    if pnl.instrument_type == "futures_mnq":
        pnl_points = round((pnl.exit_price - pnl.entry_price) * direction_mult, 2)
        pnl_usd = round(pnl_points * 2.0 * pnl.lot_size, 2)
        rr = round(pnl_points / pnl.risk_pips, 2) if pnl.risk_pips > 0 else None
        return pnl_points, pnl_usd, rr

    ps = pip_size(pnl.symbol)
    pnl_pips = round((pnl.exit_price - pnl.entry_price) / ps * direction_mult, 1)
    pip_val = pip_value_per_lot(pnl.symbol, pnl.entry_price)
    pnl_usd = round(pnl_pips * pip_val * pnl.lot_size, 2)
    rr = round(pnl_pips / pnl.risk_pips, 2) if pnl.risk_pips > 0 else None
    return pnl_pips, pnl_usd, rr


def apply_trade_filters(
    stmt: Select,
    strategy: str | None,
    symbol: str | None,
    status: str | None,
    outcome: str | None,
    date_from: date | None,
    date_to: date | None,
    instrument_type: str | None = None,
    account_id: str | None = None,
) -> Select:
    """Apply optional query filters to a trade SELECT statement."""
    if strategy is not None:
        stmt = stmt.where(TradeModel.strategy == strategy)
    if symbol is not None:
        stmt = stmt.where(TradeModel.symbol == symbol)
    if status is not None:
        stmt = stmt.where(TradeModel.status == status)
    if outcome is not None:
        stmt = stmt.where(TradeModel.outcome == outcome)
    if instrument_type is not None:
        stmt = stmt.where(TradeModel.instrument_type == instrument_type)
    if account_id is not None:
        stmt = stmt.where(TradeModel.account_id == account_id)
    if date_from is not None:
        stmt = stmt.where(
            TradeModel.open_time >= datetime.combine(
                date_from, datetime.min.time(), tzinfo=timezone.utc,
            ),
        )
    if date_to is not None:
        stmt = stmt.where(
            TradeModel.open_time <= datetime.combine(
                date_to, datetime.max.time(), tzinfo=timezone.utc,
            ),
        )
    return stmt


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
    trade: TradeModel, account_lookup: dict[str, AccountModel],
) -> dict:
    """Convert TradeModel to a dict for TradeResponse serialization."""
    account = account_lookup.get(trade.account_id) if trade.account_id else None
    return {
        "id": trade.id,
        "signal_id": trade.signal_id,
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
        "screenshot_url": trade.screenshot_url,
        "trade_metadata": trade.trade_metadata,
        "created_at": trade.created_at,
        "updated_at": trade.updated_at,
    }
