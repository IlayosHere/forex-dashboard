"""
shared/calculator.py
--------------------
Pure lot-size calculation function. No DB, no side effects.

Used by:
  - POST /api/calculate  (live recalc when user edits SL/TP in the UI)
  - Strategy scanners    (pre-calculate lot_size before persisting a Signal)

Pip value logic mirrors impulse-notifier/calculations.py so both paths
produce consistent numbers.
"""
from __future__ import annotations

import math


def _pip_size(symbol: str) -> float:
    """0.01 for JPY pairs, 0.0001 for everything else."""
    return 0.01 if "JPY" in symbol.upper() else 0.0001


def _pip_value_per_lot(symbol: str, price: float) -> float:
    """USD pip value for one standard lot (100,000 units of base currency).

    - Quote = USD  (EURUSD, GBPUSD, AUDUSD, NZDUSD): $10 flat
    - Base  = USD  (USDJPY, USDCHF, USDCAD):  (100_000 * pip) / price
    - Cross pairs: $10 fallback (conservative)
    """
    sym = symbol.upper()
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
) -> dict:
    """Calculate lot size and risk metrics for a trade.

    Parameters
    ----------
    symbol          : Currency pair or instrument, e.g. "EURUSD" or "MNQ"
    entry           : Entry price (needed for pip value on USD-base pairs)
    sl_pips         : Stop-loss distance in pips (forex) or points (futures)
    account_balance : Account equity in USD
    risk_percent    : Fraction of balance to risk, e.g. 1.0 for 1%
    tp_pips         : Take-profit distance in pips/points (optional — enables rr)
    instrument_type : "forex" (default) or "futures_mnq"

    Returns
    -------
    dict with keys:
        lot_size        : float  — lots (forex) or contracts (futures), min 1 for futures
        risk_usd        : float  — dollar amount at risk
        sl_pips         : float  — distance from entry to SL in pips/points
        rr              : float | None — reward:risk ratio (None when tp_pips not given)
        instrument_type : str    — echoed back for the response
    """
    if sl_pips == 0:
        return {
            "lot_size": 1 if instrument_type == "futures_mnq" else 0.01,
            "risk_usd": 0.0,
            "sl_pips": 0.0,
            "rr": None,
            "instrument_type": instrument_type,
        }

    risk_usd = account_balance * (risk_percent / 100.0)

    rr: float | None = None
    if tp_pips is not None:
        rr = round(tp_pips / sl_pips, 2)

    if instrument_type == "futures_mnq":
        # MNQ: $2.00 per point per contract
        raw_contracts = risk_usd / (sl_pips * 2.0)
        contracts = max(math.floor(raw_contracts), 1)
        return {
            "lot_size": contracts,
            "risk_usd": round(risk_usd, 2),
            "sl_pips": round(sl_pips, 2),
            "rr": rr,
            "instrument_type": instrument_type,
        }

    # Default: forex
    pip_value = _pip_value_per_lot(symbol, entry)
    raw_lots = risk_usd / (sl_pips * pip_value)
    lot_size = round(max(raw_lots, 0.01), 2)

    return {
        "lot_size": lot_size,
        "risk_usd": round(risk_usd, 2),
        "sl_pips": round(sl_pips, 1),
        "rr": rr,
        "instrument_type": instrument_type,
    }
