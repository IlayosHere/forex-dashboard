"""
analytics/params/liquidity.py
------------------------------
Liquidity sweep parameters: whether a prior swing high/low was swept before signal,
and how many bars elapsed between the sweep and the signal.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from analytics.params.candle_derived import _find_signal_bar
from analytics.registry import register

logger = logging.getLogger(__name__)

_LOOKBACK_BARS = 15
_OUTER_BARS = 10
_MIN_LOOKBACK = 5
_MIN_OUTER = 5


_NO_SWEEP = "none"


def _find_sweep(
    candles: pd.DataFrame,
    signal: Any,
) -> tuple[str, int] | None:
    """Return (sweep_type, sweep_bar_idx) or None on insufficient data.

    Returns ("none", -1) when search ran but found no sweep.
    Returns None when there is not enough bars to determine.
    Looks back _LOOKBACK_BARS bars from the signal for a breach of the
    swing high/low defined by the _OUTER_BARS window before that.
    """
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None

    # outer window: 10 bars before the lookback window
    outer_end = max(0, idx - _LOOKBACK_BARS)   # exclusive end = start of lookback
    outer_start = max(0, outer_end - _OUTER_BARS)
    if outer_end <= outer_start:
        return None
    outer_window = candles.iloc[outer_start:outer_end]
    if len(outer_window) < _MIN_OUTER:
        return None

    swing_high = float(outer_window["high"].max())
    swing_low = float(outer_window["low"].min())

    # lookback window: bars idx-15 to idx-1
    actual_lookback_start = max(0, idx - _LOOKBACK_BARS)
    lookback_window = candles.iloc[actual_lookback_start:idx]
    if len(lookback_window) < _MIN_LOOKBACK:
        return None

    buyside_idx: int | None = None
    sellside_idx: int | None = None

    for bar_pos in range(len(lookback_window)):
        bar = lookback_window.iloc[bar_pos]
        abs_idx = actual_lookback_start + bar_pos
        if bar["high"] > swing_high:
            if buyside_idx is None or abs_idx > buyside_idx:
                buyside_idx = abs_idx
        if bar["low"] < swing_low:
            if sellside_idx is None or abs_idx > sellside_idx:
                sellside_idx = abs_idx

    if buyside_idx is None and sellside_idx is None:
        return (_NO_SWEEP, -1)

    if buyside_idx is not None and sellside_idx is not None:
        if sellside_idx >= buyside_idx:
            return ("swept_sellside", sellside_idx)
        return ("swept_buyside", buyside_idx)

    if buyside_idx is not None:
        return ("swept_buyside", buyside_idx)
    return ("swept_sellside", sellside_idx)  # type: ignore[return-value]


@register("liquidity_swept_prior", needs_candles=True, dtype="str")
def liquidity_swept_prior(signal: Any, candles: pd.DataFrame | None) -> str | None:
    """Whether a prior swing high or low was swept in the 15 bars before signal."""
    if candles is None:
        return None
    try:
        result = _find_sweep(candles, signal)
        if result is None:
            return None
        sweep_type, _ = result
        return sweep_type
    except Exception:
        return None


@register("sweep_to_signal_bars", needs_candles=True, dtype="int")
def sweep_to_signal_bars(signal: Any, candles: pd.DataFrame | None) -> int | None:
    """Bars between the liquidity sweep and this signal (None if no sweep)."""
    if candles is None:
        return None
    try:
        result = _find_sweep(candles, signal)
        if result is None:
            return None
        sweep_type, sweep_bar_idx = result
        if sweep_type == _NO_SWEEP:
            return None
        idx = _find_signal_bar(candles, signal)
        if idx is None:
            return None
        bars = idx - sweep_bar_idx
        return int(max(1, bars))
    except Exception:
        return None
