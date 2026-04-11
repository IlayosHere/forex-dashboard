"""
analytics/params/fvg_impulse_v2.py
----------------------------------
Second batch of FVG-impulse analytics parameters, shared between the M15
and M5 variants. Split from ``fvg_impulse.py`` to respect the 200
effective-line module limit. M5-only params live in ``fvg_impulse_5m.py``.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from analytics.candle_cache import cached_atr, cached_ema20_h1, cached_h1
from analytics.params.candle_derived import (
    _analytics_pip_size,
    _atr_pips_at_bar,
    _find_signal_bar,
    _rejection_wick_pips,
)
from analytics.params.fvg_impulse import (
    _FVG_STRATEGIES,
    _find_impulse_candle,
    _meta,
)
from analytics.registry import register

logger = logging.getLogger(__name__)

_H1_TREND_BUCKET_THRESHOLD = 0.3
_H1_TREND_SLOPE_BARS = 6
_PRIOR_SWING_WINDOW = 10
_FVG_WIDTH_SPREAD_FLOOR = 0.3


@register("fvg_breathing_room_pips", strategies=_FVG_STRATEGIES, dtype="float")
def fvg_breathing_room_pips(signal: Any, _candles: pd.DataFrame | None) -> float | None:
    """Pips between signal close and FVG near edge, clamped at 0."""
    near_edge = _meta(signal).get("fvg_near_edge")
    if near_edge is None:
        return None
    pip = _analytics_pip_size(signal.symbol)
    if signal.direction == "BUY":
        room = (signal.entry - near_edge) / pip
    else:
        room = (near_edge - signal.entry) / pip
    return float(max(0.0, room))


@register("rejection_wick_atr", strategies=_FVG_STRATEGIES, needs_candles=True, dtype="float")
def rejection_wick_atr(signal: Any, candles: pd.DataFrame | None) -> float | None:
    """Signal-bar rejection wick in pips divided by ATR-14 in pips."""
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    bar = candles.iloc[idx]
    pip = _analytics_pip_size(signal.symbol)
    wick_pips = _rejection_wick_pips(bar, signal.direction, pip)
    if wick_pips is None:
        return None
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return float(wick_pips / atr_pips)


@register("c1_close_strength", strategies=_FVG_STRATEGIES, needs_candles=True, dtype="float")
def c1_close_strength(signal: Any, candles: pd.DataFrame | None) -> float | None:
    """Direction-aware close position of C1 within its own range (0-1)."""
    if candles is None:
        return None
    c1_idx = _find_impulse_candle(candles, _meta(signal))
    if c1_idx is None:
        return None
    c1 = candles.iloc[c1_idx]
    rng = c1["high"] - c1["low"]
    if rng <= 0:
        return None
    if signal.direction == "BUY":
        pos = (c1["close"] - c1["low"]) / rng
    else:
        pos = (c1["high"] - c1["close"]) / rng
    return float(max(0.0, min(1.0, pos)))


@register("c1_broke_prior_swing", strategies=_FVG_STRATEGIES, needs_candles=True, dtype="bool")
def c1_broke_prior_swing(signal: Any, candles: pd.DataFrame | None) -> bool | None:
    """Whether C1 closed beyond the extreme of the prior 10 bars."""
    if candles is None:
        return None
    c1_idx = _find_impulse_candle(candles, _meta(signal))
    if c1_idx is None:
        return None
    window_start = c1_idx - _PRIOR_SWING_WINDOW
    if window_start < 0:
        return None
    window = candles.iloc[window_start:c1_idx]
    if len(window) < _PRIOR_SWING_WINDOW:
        return None
    c1 = candles.iloc[c1_idx]
    if signal.direction == "BUY":
        return bool(c1["close"] > window["high"].max())
    return bool(c1["close"] < window["low"].min())


@register("opposing_wick_ratio", strategies=_FVG_STRATEGIES, needs_candles=True, dtype="float")
def opposing_wick_ratio(signal: Any, candles: pd.DataFrame | None) -> float | None:
    """Wrong-side wick as a share of the signal bar's total range."""
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    bar = candles.iloc[idx]
    rng = bar["high"] - bar["low"]
    if rng <= 0:
        return None
    if signal.direction == "BUY":
        wick = bar["high"] - max(bar["open"], bar["close"])
    else:
        wick = min(bar["open"], bar["close"]) - bar["low"]
    if wick < 0:
        return None
    return float(wick / rng)


@register("spread_dominance", strategies=_FVG_STRATEGIES, dtype="float")
def spread_dominance(signal: Any, _candles: pd.DataFrame | None) -> float | None:
    """Bounded share of spread in total cost-adjusted risk."""
    total = signal.risk_pips + signal.spread_pips
    if total <= 0:
        return None
    return float(signal.spread_pips / total)


@register("fvg_width_spread_mult", strategies=_FVG_STRATEGIES, dtype="float")
def fvg_width_spread_mult(signal: Any, _candles: pd.DataFrame | None) -> float | None:
    """How many spread-widths the FVG spans (floor 0.3 on denominator)."""
    width = _meta(signal).get("fvg_width_pips")
    if width is None:
        return None
    denom = max(signal.spread_pips, _FVG_WIDTH_SPREAD_FLOOR)
    return float(width / denom)


@register("h1_trend_strength_bucket", strategies=_FVG_STRATEGIES, needs_candles=True, dtype="str")
def h1_trend_strength_bucket(signal: Any, candles: pd.DataFrame | None) -> str | None:
    """H1 EMA-20 slope z-score bucketed as WITH / FLAT / AGAINST."""
    if candles is None:
        return None
    h1 = cached_h1(candles)
    idx = _find_signal_bar(h1, signal)
    if idx is None or idx < _H1_TREND_SLOPE_BARS:
        return None
    ema_20 = cached_ema20_h1(h1)
    slope_raw = ema_20.iloc[idx] - ema_20.iloc[idx - _H1_TREND_SLOPE_BARS]
    slope_pips = slope_raw / _analytics_pip_size(signal.symbol)
    h1_atr_series = cached_atr(h1, period=14)
    if idx >= len(h1_atr_series) or pd.isna(h1_atr_series.iloc[idx]):
        return None
    h1_atr_pips = float(h1_atr_series.iloc[idx]) / _analytics_pip_size(signal.symbol)
    if h1_atr_pips == 0:
        return None
    z = slope_pips / h1_atr_pips
    if signal.direction == "SELL":
        z = -z
    if z > _H1_TREND_BUCKET_THRESHOLD:
        return "WITH"
    if z < -_H1_TREND_BUCKET_THRESHOLD:
        return "AGAINST"
    return "FLAT"
