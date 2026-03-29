"""
calculations.py - Trade parameter calculations for Nova candle signals.

Computes SL (BOS-based), TP, lot size and risk in pips.
Entry is at candle open (no-wick side — limit order for retracement).
SL uses the snake_line zigzag to find the last structural swing point.

Account assumptions
-------------------
- Account equity : $50,000
- Risk per trade : 1% = $500
- SL             : BOS swing + 3 pip buffer
- RR             : 1:1 (TP = entry +/- raw_risk)
- Slippage       : 0.2 pips
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from shared.calculator import pip_size, pip_value_per_lot
from strategies.fvg_impulse.config import EXCHANGE_TZ, SLIPPAGE_PIPS, get_spread_pips
from strategies.nova_candle.sl import compute_bos_sl

logger = logging.getLogger(__name__)

SL_BUFFER_PIPS: float = 3.0
ACCOUNT_RISK_USD: float = 500.0  # $50k * 1%


def calculate_trade_params(
    signal: dict[str, Any],
    candles: pd.DataFrame,
    signal_idx: int,
) -> dict[str, Any]:
    """Compute BOS-based SL, TP, lot size and risk pips.

    Parameters
    ----------
    signal : dict from scanner.find_nova_candle(). Must contain:
        symbol, direction, open, candle_time.
    candles : full M15 DataFrame used for the scan (OHLC, UTC index).
    signal_idx : integer position of the signal candle in *candles*.

    Returns
    -------
    dict with sl, tp, lot_size, risk_pips, spread_pips.
    Returns None values if no valid BOS swing is found.
    """
    symbol = signal["symbol"]
    direction = signal["direction"]
    entry = signal["open"]  # limit order at candle open (no-wick side)
    candle_time = signal["candle_time"]

    pip = pip_size(symbol)
    dir_int = 0 if direction == "BUY" else 1

    highs = candles["high"].values.astype(np.float64)
    lows = candles["low"].values.astype(np.float64)
    closes = candles["close"].values.astype(np.float64)

    sl, swing_idx = compute_bos_sl(
        highs=highs, lows=lows, closes=closes,
        signal_idx=signal_idx, direction=dir_int,
        pip=pip, buffer_pips=SL_BUFFER_PIPS, entry=entry,
    )

    if sl is None:
        logger.warning("No valid BOS swing for %s %s @ %s", symbol, direction, candle_time)
        return _fallback_params(signal, candle_time, pip, candles)

    # BOS metadata: candle time and raw swing price (before buffer)
    bos_time = candles.index[swing_idx].to_pydatetime()
    bos_price = float(highs[swing_idx]) if dir_int == 1 else float(lows[swing_idx])

    result = _build_params(signal, sl, entry, pip, candle_time)
    result["bos_candle_time"] = bos_time
    result["bos_swing_price"] = bos_price
    return result


def _build_params(
    signal: dict[str, Any],
    sl: float,
    entry: float,
    pip: float,
    candle_time,
) -> dict[str, Any]:
    """Build the final trade parameter dict from BOS SL."""
    symbol = signal["symbol"]
    direction = signal["direction"]

    broker_hour = candle_time.astimezone(EXCHANGE_TZ).hour
    spread_pips = get_spread_pips(symbol, broker_hour)

    raw_risk_pips = abs(entry - sl) / pip
    effective_risk_pips = raw_risk_pips + spread_pips + SLIPPAGE_PIPS

    if direction == "BUY":
        tp = entry + raw_risk_pips * pip
    else:
        tp = entry - raw_risk_pips * pip

    pv = pip_value_per_lot(symbol, entry)
    lot_size = ACCOUNT_RISK_USD / (effective_risk_pips * pv)
    lot_size = round(max(lot_size, 0.01), 2)

    return {
        "sl": sl,
        "tp": tp,
        "lot_size": lot_size,
        "risk_pips": round(effective_risk_pips, 1),
        "spread_pips": round(spread_pips, 1),
    }


def _fallback_params(
    signal: dict[str, Any],
    candle_time,
    pip: float,
    candles: pd.DataFrame,
) -> dict[str, Any]:
    """Fallback when no BOS swing is found — use candle extreme + buffer."""
    direction = signal["direction"]
    entry = signal["open"]

    if direction == "BUY":
        sl = signal["low"] - SL_BUFFER_PIPS * pip
    else:
        sl = signal["high"] + SL_BUFFER_PIPS * pip

    result = _build_params(signal, sl, entry, pip, candle_time)
    result["bos_candle_time"] = None
    result["bos_swing_price"] = None
    return result
