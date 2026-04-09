"""
analytics/params/candle_derived.py
----------------------------------
Shared candle-dependent parameters for ALL strategies.

Provides ATR, trend alignment, volatility percentile, and risk/ATR ratio.
Also exports ``_find_signal_bar`` and ``_atr_pips_at_bar`` helpers for use by
other param modules.
"""
from __future__ import annotations

import logging
from datetime import timezone
from typing import Any

import pandas as pd

from analytics.candle_cache import _compute_atr
from analytics.registry import register
from shared.calculator import pip_size

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers (imported by fvg_impulse.py and nova_candle.py)
# ---------------------------------------------------------------------------

def _find_signal_bar(candles: pd.DataFrame, signal: Any) -> int | None:
    """Find the index position of the signal's candle_time in the DataFrame."""
    target = signal.candle_time
    if hasattr(target, "tzinfo") and target.tzinfo is None:
        target = target.replace(tzinfo=timezone.utc)
    try:
        idx = candles.index.get_indexer([target], method="ffill")[0]
        if idx < 0:
            return None
        return idx
    except (KeyError, IndexError):
        return None


def _atr_pips_at_bar(
    candles: pd.DataFrame,
    signal: Any,
) -> float | None:
    """Return ATR-14 in pips at the signal bar, or None."""
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    atr_series = _compute_atr(candles)
    if idx >= len(atr_series) or pd.isna(atr_series.iloc[idx]):
        return None
    return float(atr_series.iloc[idx]) / pip_size(signal.symbol)


# ---------------------------------------------------------------------------
# Registered params
# ---------------------------------------------------------------------------

@register("atr_14", needs_candles=True, dtype="float")
def atr_14(signal: Any, candles: pd.DataFrame | None) -> float | None:
    """Return 14-period ATR in pips at the signal bar."""
    if candles is None:
        return None
    return _atr_pips_at_bar(candles, signal)


@register("trend_h1_aligned", needs_candles=True, dtype="bool")
def trend_h1_aligned(
    signal: Any,
    candles: pd.DataFrame | None,
) -> bool | None:
    """Check if H1 EMA-20 trend aligns with signal direction."""
    if candles is None:
        return None
    h1 = candles.resample("1h").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"},
    ).dropna()
    if len(h1) < 24:
        return None
    ema_20 = h1["close"].ewm(span=20, adjust=False).mean()
    if len(ema_20) < 4:
        return None
    rising = ema_20.iloc[-1] > ema_20.iloc[-4]
    if signal.direction == "BUY":
        return rising
    return not rising


@register("volatility_percentile", needs_candles=True, dtype="float")
def volatility_percentile(
    signal: Any,
    candles: pd.DataFrame | None,
) -> float | None:
    """Return the current ATR's percentile rank within the last 20 values."""
    if candles is None:
        return None
    atr_series = _compute_atr(candles).dropna()
    if len(atr_series) < 20:
        return None
    last_20 = atr_series.iloc[-20:]
    current = atr_series.iloc[-1]
    count_le = int((last_20 <= current).sum())
    return count_le / len(last_20) * 100


@register("risk_pips_atr", needs_candles=True, dtype="float")
def risk_pips_atr(
    signal: Any,
    candles: pd.DataFrame | None,
) -> float | None:
    """Return signal.risk_pips divided by ATR-14 in pips."""
    if candles is None:
        return None
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return signal.risk_pips / atr_pips
