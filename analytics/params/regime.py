"""
analytics/params/regime.py
--------------------------
Cross-strategy regime / momentum / cost parameters (themes D-E).

Four parameters: Kaufman efficiency ratio, pre-signal compression,
direction-oriented trail extension, and spread/ATR cost proxy. All use
the strategy's native timeframe (via ``_find_signal_bar`` on the shared
cache DataFrame) and apply to every strategy.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from analytics.params.candle_derived import _analytics_pip_size, _atr_pips_at_bar, _find_signal_bar
from analytics.registry import register

logger = logging.getLogger(__name__)

_EFFICIENCY_WINDOW = 50
_COMPRESSION_WINDOW = 5
_TRAIL_LOOKBACK = 10


@register("range_bound_efficiency", needs_candles=True, dtype="float")
def range_bound_efficiency(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Kaufman efficiency ratio (0..1) over the prior 50 bars.

    0 means pure chop (gross path >> net displacement), 1 means a clean
    one-way move. Window is the 50 bars ending at (and including) the
    signal's own bar.
    """
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None or idx < _EFFICIENCY_WINDOW:
        return None
    window = candles.iloc[idx - (_EFFICIENCY_WINDOW - 1):idx + 1]
    closes = window["close"].to_numpy()
    net = abs(float(closes[-1]) - float(closes[0]))
    gross = float(np.sum(np.abs(np.diff(closes))))
    if gross == 0:
        return None
    return float(net / gross)


@register("range_compression_ratio", needs_candles=True, dtype="float")
def range_compression_ratio(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Range of the 5 bars before the signal bar divided by ATR-14 in pips."""
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None or idx < _COMPRESSION_WINDOW:
        return None
    pre = candles.iloc[idx - _COMPRESSION_WINDOW:idx]
    high = float(pre["high"].max())
    low = float(pre["low"].min())
    range_pips = (high - low) / _analytics_pip_size(signal.symbol)
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return float(range_pips / atr_pips)


@register("trail_extension_atr", needs_candles=True, dtype="float")
def trail_extension_atr(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Signed 10-bar close-delta in ATR units, oriented with signal direction.

    Positive values always mean "price is extended in the signal's favor";
    negative values mean the signal is fading into a recent counter-move.
    """
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None or idx < _TRAIL_LOOKBACK:
        return None
    pip = _analytics_pip_size(signal.symbol)
    delta_price = float(
        candles["close"].iloc[idx] - candles["close"].iloc[idx - _TRAIL_LOOKBACK],
    )
    delta_pips = delta_price / pip
    if signal.direction == "SELL":
        delta_pips = -delta_pips
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return float(delta_pips / atr_pips)


@register("spread_atr_ratio", needs_candles=True, dtype="float")
def spread_atr_ratio(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Spread cost in pips divided by ATR-14 in pips — expected-cost proxy."""
    if candles is None:
        return None
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return float(signal.spread_pips / atr_pips)
