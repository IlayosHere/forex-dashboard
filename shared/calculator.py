"""
shared/calculator.py
--------------------
Pure lot-size calculation function. No DB, no side effects.

Used by:
  - POST /api/calculate  (live recalc when user edits SL/TP in the UI)
  - Strategy scanners    (pre-calculate lot_size before persisting a Signal)

Pip value logic mirrors impulse-notifier/calculations.py so both paths
produce consistent numbers.

Futures multipliers are driven by symbol, not instrument_type:
  MNQ → $2.00/point/contract
  MES → $5.00/point/contract
instrument_type is only used to distinguish "futures" (any) from "forex".
"""
from __future__ import annotations

import math
from typing import Any

# Dollars per point per contract, keyed by futures symbol.
# Add new contracts here — no other code changes needed.
_FUTURES_DOLLARS_PER_POINT: dict[str, float] = {
    "MNQ": 2.0,   # Micro E-mini Nasdaq-100
    "MES": 5.0,   # Micro E-mini S&P 500
}


def is_futures_symbol(symbol: str) -> bool:
    """Return True if symbol is a known futures contract."""
    return symbol.upper() in _FUTURES_DOLLARS_PER_POINT


def futures_dollars_per_point(symbol: str) -> float:
    """Return the dollar-per-point multiplier for a futures symbol.

    Raises KeyError if the symbol is not a known futures contract.
    """
    return _FUTURES_DOLLARS_PER_POINT[symbol.upper()]


def pip_size(symbol: str) -> float:
    """0.01 for JPY pairs, 0.0001 for everything else."""
    return 0.01 if "JPY" in symbol.upper().replace("/", "") else 0.0001


def pip_value_per_lot(symbol: str, price: float) -> float:
    """USD pip value for one standard lot (100,000 units of base currency).

    - Quote = USD  (EURUSD, GBPUSD, AUDUSD, NZDUSD): $10 flat
    - Base  = USD  (USDJPY, USDCHF, USDCAD):  (100_000 * pip) / price
    - Cross pairs: $10 fallback (conservative)
    """
    sym = symbol.upper().replace("/", "")
    if sym.endswith("USD"):
        return 10.0
    if sym.startswith("USD"):
        pip = 0.01 if sym.endswith("JPY") else 0.0001
        return (100_000 * pip) / price
    return 10.0  # cross pair fallback


def calculate_lot_size(
    symbol: str,
    entry: float,
    sl_pips: float,
    account_balance: float,
    risk_percent: float,
    tp_pips: float | None = None,
    instrument_type: str = "forex",
) -> dict[str, Any]:
    """Calculate lot size and risk metrics for a trade.

    Parameters
    ----------
    symbol          : Currency pair or futures contract, e.g. "EURUSD", "MNQ", "MES"
    entry           : Entry price (needed for pip value on USD-base pairs)
    sl_pips         : Stop-loss distance in pips (forex) or points (futures)
    account_balance : Account equity in USD
    risk_percent    : Fraction of balance to risk, e.g. 1.0 for 1%
    tp_pips         : Take-profit distance in pips/points (optional — enables rr)
    instrument_type : "forex" (default) or "futures" — only used to select
                      the forex vs futures calculation path; contract multiplier
                      is derived from symbol, not this field.

    Returns
    -------
    dict with keys:
        lot_size        : float  — lots (forex) or contracts (futures), min 1 for futures
        risk_usd        : float  — dollar amount at risk
        sl_pips         : float  — distance from entry to SL in pips/points
        rr              : float | None — reward:risk ratio (None when tp_pips not given)
        instrument_type : str    — echoed back for the response
    """
    # Resolve whether this is a futures trade from the symbol itself
    sym_upper = symbol.upper()
    is_futures = instrument_type.startswith("futures") or is_futures_symbol(sym_upper)

    if sl_pips <= 0:
        return {
            "lot_size": 1 if is_futures else 0.01,
            "risk_usd": 0.0,
            "sl_pips": 0.0,
            "rr": None,
            "instrument_type": instrument_type,
        }

    risk_usd = account_balance * (risk_percent / 100.0)

    rr: float | None = None
    if tp_pips is not None:
        rr = round(tp_pips / sl_pips, 2)

    if is_futures:
        # Contract multiplier comes from symbol: MNQ=$2/pt, MES=$5/pt
        dollars_per_point = _FUTURES_DOLLARS_PER_POINT.get(sym_upper, 2.0)
        raw_contracts = risk_usd / (sl_pips * dollars_per_point)
        contracts = max(math.floor(raw_contracts), 1)
        return {
            "lot_size": contracts,
            "risk_usd": round(risk_usd, 2),
            "sl_pips": round(sl_pips, 2),
            "rr": rr,
            "instrument_type": instrument_type,
        }

    # Default: forex
    pip_value = pip_value_per_lot(symbol, entry)
    raw_lots = risk_usd / (sl_pips * pip_value)
    lot_size = round(max(raw_lots, 0.01), 2)
    min_lot_applied = lot_size > raw_lots

    if min_lot_applied:
        risk_usd = lot_size * sl_pips * pip_value

    return {
        "lot_size": lot_size,
        "risk_usd": round(risk_usd, 2),
        "sl_pips": round(sl_pips, 1),
        "rr": rr,
        "instrument_type": instrument_type,
        "min_lot_applied": min_lot_applied,
    }
