"""
analytics/params/volume.py
--------------------------
Volume-based candle parameters for all strategies.

All three params use TradingView tick count as an activity proxy — FX has
no central exchange volume. Returns None gracefully when volume data is
unavailable for a pair or broker.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from analytics.params.candle_derived import _find_signal_bar
from analytics.registry import register

logger = logging.getLogger(__name__)

_VOL_REGIME_LOW = 0.7
_VOL_REGIME_HIGH = 1.5
_VOL_BASELINE_BARS = 20
_VOL_PERCENTILE_BARS = 50


def _bar_volume(candles: pd.DataFrame, idx: int) -> float | None:
    """Return the volume at integer position ``idx``, or None if missing or NaN."""
    if "volume" not in candles.columns:
        return None
    raw = candles["volume"].iloc[idx]
    if pd.isna(raw):
        return None
    return float(raw)


@register("relative_volume", needs_candles=True, dtype="float")
def relative_volume(
    signal: Any,
    candles: pd.DataFrame | None,
) -> float | None:
    """Signal-bar volume divided by the mean volume of the prior 20 bars.

    Volume here is TradingView tick count, not traded lot volume — FX has
    no central exchange. Values >1 indicate above-average participation at
    the signal bar; values <1 indicate a quieter-than-average bar.
    Returns None when volume data is unavailable for the pair or when
    there are fewer than 20 prior bars.
    """
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None or idx < _VOL_BASELINE_BARS:
        return None
    bar_vol = _bar_volume(candles, idx)
    if bar_vol is None:
        return None
    baseline = candles["volume"].iloc[idx - _VOL_BASELINE_BARS:idx]
    if baseline.isna().any():
        return None
    baseline_mean = float(baseline.mean())
    if baseline_mean <= 0:
        return None
    return bar_vol / baseline_mean


@register("volume_percentile", needs_candles=True, dtype="float")
def volume_percentile(
    signal: Any,
    candles: pd.DataFrame | None,
) -> float | None:
    """Percentile rank (0-100) of signal-bar volume within the last 50 bars.

    Uses tick count as activity proxy, not traded lot volume — FX has no
    central exchange. Returns None when volume data is unavailable or when
    there are fewer than 50 bars of history at the signal bar.
    """
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    bar_vol = _bar_volume(candles, idx)
    if bar_vol is None:
        return None
    start = max(0, idx - (_VOL_PERCENTILE_BARS - 1))
    window = candles["volume"].iloc[start:idx + 1]
    if len(window) < _VOL_PERCENTILE_BARS or window.isna().any():
        return None
    count_le = int((window <= bar_vol).sum())
    return float(count_le / len(window) * 100)


@register("volume_regime", needs_candles=True, dtype="str")
def volume_regime(
    signal: Any,
    candles: pd.DataFrame | None,
) -> str | None:
    """Categorical volume regime derived from relative_volume.

    Buckets tick-count activity (not traded lot volume) into low / normal /
    high relative to the 20-bar baseline. Returns None when relative_volume
    cannot be computed.
    """
    rv = relative_volume(signal, candles)
    if rv is None:
        return None
    if rv < _VOL_REGIME_LOW:
        return "low"
    if rv > _VOL_REGIME_HIGH:
        return "high"
    return "normal"
