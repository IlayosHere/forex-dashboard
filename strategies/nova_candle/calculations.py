"""
calculations.py - Trade parameter calculations for Nova (wickless momentum) candle signals.

Computes SL, TP, lot size and risk in pips for a given scanner signal dict.
Uses per-pair spread tables from config (3-tier: H0/H1/normal)
and a fixed 0.2 pip slippage assumption.

Account assumptions
-------------------
- Account equity : $50,000
- Risk per trade : 1% = $500
- SL buffer      : 4 pips beyond the candle extreme
- RR             : 1:1 (TP = entry +/- effective_risk)
- Slippage       : 0.2 pips (both entry and stop exits included in risk calc)
"""
from __future__ import annotations

from typing import Any, Dict

from strategies.fvg_impulse.config import EXCHANGE_TZ, get_spread_pips

SLIPPAGE_PIPS: float = 0.2
SL_BUFFER_PIPS: float = 4.0
ACCOUNT_RISK_USD: float = 500.0  # $50k * 1%


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pip_size(symbol: str) -> float:
    """Return pip size: 0.01 for JPY pairs, 0.0001 for all others."""
    return 0.01 if "JPY" in symbol.upper() else 0.0001


def _pip_value_per_lot(symbol: str, price: float) -> float:
    """Return USD pip value per standard lot (100,000 units of base currency).

    Parameters
    ----------
    symbol : Currency pair string (e.g. "EURUSD", "USDJPY").
    price  : Current mid price used for USD conversion on non-USD-quote pairs.

    Logic
    -----
    - Quote = USD  (EURUSD, GBPUSD, AUDUSD, NZDUSD): pip_value = $10 flat.
    - Base  = USD  (USDJPY, USDCHF, USDCAD):
        pip_value = lot_size * pip_size / price  (converts quote CCY -> USD).
    - Cross pairs: fallback $10 (not in default scan list).
    """
    sym = symbol.upper()
    if sym.endswith("USD"):
        return 10.0
    if sym.startswith("USD"):
        pip = 0.01 if sym.endswith("JPY") else 0.0001
        return (100_000 * pip) / price
    return 10.0  # cross pair fallback


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------

def calculate_trade_params(signal: Dict[str, Any]) -> Dict[str, Any]:
    """Compute SL, TP, lot size and risk pips for a nova candle signal.

    Parameters
    ----------
    signal : dict returned by scanner.find_nova_candle(). Must contain:
        symbol, direction ("BUY"/"SELL"), close, low, high, candle_time.

    Returns
    -------
    dict with keys:
        sl          - SL order price
        tp          - TP order price
        lot_size    - Rounded lot size (min 0.01)
        risk_pips   - Effective risk in pips (incl. spread + slippage)
        spread_pips - Spread used for this symbol/hour
    """
    symbol = signal["symbol"]
    direction = signal["direction"]   # "BUY" or "SELL"
    close = signal["close"]
    low = signal["low"]
    high = signal["high"]
    candle_time = signal["candle_time"]  # UTC datetime

    pip = _pip_size(symbol)

    # Derive broker hour from UTC candle_time using the exchange timezone.
    # Handles DST automatically (UTC+2 winter / UTC+3 summer).
    broker_hour = candle_time.astimezone(EXCHANGE_TZ).hour
    spread_pips = get_spread_pips(symbol, broker_hour)

    # SL price: 4 pips beyond candle extreme in loss direction
    if direction == "BUY":
        sl = low - SL_BUFFER_PIPS * pip
        raw_risk_pips = (close - sl) / pip
    else:
        sl = high + SL_BUFFER_PIPS * pip
        raw_risk_pips = (sl - close) / pip

    # Effective risk = distance to stop + spread (entry cost) + slippage
    effective_risk_pips = raw_risk_pips + spread_pips + SLIPPAGE_PIPS

    # TP at 1:1: mirror raw SL distance from entry (spread/slippage affect lot size only)
    if direction == "BUY":
        tp = close + raw_risk_pips * pip
    else:
        tp = close - raw_risk_pips * pip

    # Lot size: risk_usd / (risk_pips * pip_value_per_lot)
    pv = _pip_value_per_lot(symbol, close)
    lot_size = ACCOUNT_RISK_USD / (effective_risk_pips * pv)
    lot_size = round(max(lot_size, 0.01), 2)

    return {
        "sl": sl,
        "tp": tp,
        "lot_size": lot_size,
        "risk_pips": round(effective_risk_pips, 1),
        "spread_pips": round(spread_pips, 1),
    }
