"""
shared/calculator.py
--------------------
Pure contract-size calculation function. No DB, no side effects.

Used by:
  - POST /api/calculate  (live recalc when user edits SL/TP in the UI)
  - Strategy scanners    (pre-calculate lot_size before persisting a Signal)

Futures multipliers are driven by symbol:
  MNQ → $2.00/point/contract
  MES → $5.00/point/contract
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


def calculate_lot_size(
    symbol: str,
    entry: float,
    sl_points: float,
    account_balance: float,
    risk_percent: float,
    tp_points: float | None = None,
    instrument_type: str = "futures",
) -> dict[str, Any]:
    """Calculate contract size and risk metrics for a trade.

    Parameters
    ----------
    symbol          : Futures contract, e.g. "MNQ", "MES"
    entry           : Entry price
    sl_points       : Stop-loss distance in points
    account_balance : Account equity in USD
    risk_percent    : Fraction of balance to risk, e.g. 1.0 for 1%
    tp_points       : Take-profit distance in points (optional — enables rr)
    instrument_type : echoed back for the response

    Returns
    -------
    dict with keys:
        lot_size        : float  — contracts, min 1
        risk_usd        : float  — dollar amount at risk
        sl_points       : float  — distance from entry to SL in points
        rr              : float | None — reward:risk ratio (None when tp_points not given)
        instrument_type : str    — echoed back for the response
    """
    sym_upper = symbol.upper()

    if sl_points <= 0:
        return {
            "lot_size": 1,
            "risk_usd": 0.0,
            "sl_points": 0.0,
            "rr": None,
            "instrument_type": instrument_type,
        }

    risk_usd = account_balance * (risk_percent / 100.0)

    rr: float | None = None
    if tp_points is not None:
        rr = round(tp_points / sl_points, 2)

    dollars_per_point = _FUTURES_DOLLARS_PER_POINT.get(sym_upper, 2.0)
    raw_contracts = risk_usd / (sl_points * dollars_per_point)
    contracts = max(math.floor(raw_contracts), 1)
    return {
        "lot_size": contracts,
        "risk_usd": round(risk_usd, 2),
        "sl_points": round(sl_points, 2),
        "rr": rr,
        "instrument_type": instrument_type,
    }
