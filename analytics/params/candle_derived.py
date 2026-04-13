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

from analytics.candle_cache import cached_atr, cached_ema20_h1, cached_h1
from analytics.registry import register
from shared.calculator import pip_size

logger = logging.getLogger(__name__)

# Instrument-specific pip sizes for non-forex symbols.
# shared.calculator.pip_size only handles JPY vs. rest (0.01 / 0.0001).
# Metals and indices need their own conventions to keep ATR/pips meaningful.
#   XAUUSD/XAGUSD: quoted to 2 d.p. → 1 pip = 0.01 (same as JPY).
#   MNQ/NQ: minimum tick = 0.25 index points → treat 0.25 as 1 "pip".
_INSTRUMENT_PIP_OVERRIDES: dict[str, float] = {
    "XAUUSD": 0.01,
    "XAGUSD": 0.01,
    "XPTUSD": 0.01,
    "MNQ": 0.25,
    "NQ": 0.25,
    "ES": 0.25,
    "MES": 0.25,
}


def _analytics_pip_size(symbol: str) -> float:
    """Return analytics-layer pip size, with overrides for non-forex instruments."""
    return _INSTRUMENT_PIP_OVERRIDES.get(symbol, pip_size(symbol))

_VOL_REGIME_LOW = 0.7
_VOL_REGIME_HIGH = 1.5
_VOL_BASELINE_BARS = 20
_VOL_PERCENTILE_BARS = 50


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
    atr_series = cached_atr(candles)
    if idx >= len(atr_series) or pd.isna(atr_series.iloc[idx]):
        return None
    return float(atr_series.iloc[idx]) / _analytics_pip_size(signal.symbol)


def _signal_meta(signal: Any) -> dict[str, Any]:
    """Return signal_metadata dict safely (empty dict when absent or None)."""
    return getattr(signal, "signal_metadata", {}) or {}


def _rejection_wick_pips(
    bar: pd.Series, direction: str, pip: float,
) -> float | None:
    """Compute the rejection wick in pips for a given bar and direction.

    BUY rejection wick = lower wick (low to min(open, close)).
    SELL rejection wick = upper wick (max(open, close) to high).
    Returns None when the wick is negative (malformed bar data).
    """
    if direction == "BUY":
        wick_pips = (min(bar["open"], bar["close"]) - bar["low"]) / pip
    else:
        wick_pips = (bar["high"] - max(bar["open"], bar["close"])) / pip
    return float(wick_pips) if wick_pips >= 0 else None


def _volume_at_bar(candles: pd.DataFrame, signal: Any) -> float | None:
    """Return the volume value at the signal bar, or None.

    Returns None when:
      - the candles DataFrame has no 'volume' column (pair/broker without
        volume support)
      - the signal bar cannot be located in the candles index
      - the resolved volume is NaN
    """
    if "volume" not in candles.columns:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    raw = candles["volume"].iloc[idx]
    if pd.isna(raw):
        return None
    return float(raw)


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
    """Check if the H1 EMA-20 trend at signal time aligns with signal direction.

    Compares EMA-20 at the signal's H1 bar to the EMA-20 three H1 bars earlier.
    Returns None when the signal's H1 bar is outside the fetched window or when
    fewer than 24 H1 bars of history are available.
    """
    if candles is None:
        return None
    h1 = cached_h1(candles)
    if len(h1) < 24:
        return None
    idx = _find_signal_bar(h1, signal)
    if idx is None or idx < 3:
        return None
    ema_20 = cached_ema20_h1(h1)
    rising = bool(ema_20.iloc[idx] > ema_20.iloc[idx - 3])
    if signal.direction == "BUY":
        return rising
    return not rising


@register("volatility_percentile", needs_candles=True, dtype="float")
def volatility_percentile(
    signal: Any,
    candles: pd.DataFrame | None,
) -> float | None:
    """Percentile rank of the signal bar's ATR within the prior 20 bars.

    "Prior 20" means the 20 bars ending at (and including) the signal's own bar,
    using the strategy's native timeframe (~5h on M15, ~1h40m on M5). Returns
    None when the signal bar is outside the fetched window or when there are
    fewer than 20 non-NaN ATR values at the signal bar.
    """
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    atr_series = cached_atr(candles)
    if idx >= len(atr_series):
        return None
    window_start = max(0, idx - 19)
    window = atr_series.iloc[window_start:idx + 1].dropna()
    if len(window) < 20:
        return None
    current = atr_series.iloc[idx]
    if pd.isna(current):
        return None
    count_le = int((window <= current).sum())
    return count_le / len(window) * 100


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
    bar_vol = _volume_at_bar(candles, signal)
    if bar_vol is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None or idx < _VOL_BASELINE_BARS:
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
    bar_vol = _volume_at_bar(candles, signal)
    if bar_vol is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    start = max(0, idx - (_VOL_PERCENTILE_BARS - 1))
    window = candles["volume"].iloc[start:idx + 1]
    if len(window) < _VOL_PERCENTILE_BARS or window.isna().any():
        return None
    count_le = int((window <= bar_vol).sum())
    return count_le / len(window) * 100


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
