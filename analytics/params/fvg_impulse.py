"""
analytics/params/fvg_impulse.py
-------------------------------
Parameters for FVG-impulse strategies: metadata-derived and candle-dependent.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from analytics.params.candle_derived import _atr_pips_at_bar, _find_signal_bar
from analytics.registry import register
from shared.calculator import pip_size

logger = logging.getLogger(__name__)

_FVG_STRATEGIES: frozenset[str] = frozenset({"fvg-impulse", "fvg-impulse-5m"})


def _meta(signal: Any) -> dict[str, Any]:
    """Return signal_metadata dict safely."""
    return getattr(signal, "signal_metadata", {}) or {}


# ---------------------------------------------------------------------------
# Metadata-only params
# ---------------------------------------------------------------------------

@register("fvg_age", strategies=_FVG_STRATEGIES, dtype="int")
def fvg_age(signal: Any, _candles: pd.DataFrame | None) -> int | None:
    """Return the FVG age (number of candles since formation)."""
    return _meta(signal).get("fvg_age")


@register("fvg_width_pips", strategies=_FVG_STRATEGIES, dtype="float")
def fvg_width_pips(signal: Any, _candles: pd.DataFrame | None) -> float | None:
    """Return the FVG gap width in pips."""
    return _meta(signal).get("fvg_width_pips")


# ---------------------------------------------------------------------------
# Candle-dependent params
# ---------------------------------------------------------------------------

@register(
    "fvg_width_atr_ratio", strategies=_FVG_STRATEGIES,
    needs_candles=True, dtype="float",
)
def fvg_width_atr_ratio(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Return fvg_width_pips / ATR-14 in pips."""
    if candles is None:
        return None
    width = _meta(signal).get("fvg_width_pips")
    if width is None:
        return None
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return width / atr_pips


@register(
    "wick_penetration_ratio", strategies=_FVG_STRATEGIES,
    needs_candles=True, dtype="float",
)
def wick_penetration_ratio(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Return how far the signal candle wick penetrates into the FVG (0-1)."""
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    meta = _meta(signal)
    near_edge = meta.get("fvg_near_edge")
    fvg_width = meta.get("fvg_width_pips")
    if near_edge is None or fvg_width is None or fvg_width == 0:
        return None
    bar = candles.iloc[idx]
    fvg_height_price = fvg_width * pip_size(signal.symbol)
    if signal.direction == "BUY":
        ratio = (near_edge - bar["low"]) / fvg_height_price
    else:
        ratio = (bar["high"] - near_edge) / fvg_height_price
    return max(0.0, min(1.0, ratio))


@register(
    "rejection_body_ratio", strategies=_FVG_STRATEGIES,
    needs_candles=True, dtype="float",
)
def rejection_body_ratio(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Return signal candle's close position relative to its range."""
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    bar = candles.iloc[idx]
    range_ = bar["high"] - bar["low"]
    if range_ <= 0:
        return None
    if signal.direction == "BUY":
        return (bar["close"] - bar["low"]) / range_
    return (bar["high"] - bar["close"]) / range_


def _find_impulse_candle(
    candles: pd.DataFrame, meta: dict[str, Any],
) -> int | None:
    """Find the impulse candle (C1) index from fvg_formation_time."""
    ft_raw = meta.get("fvg_formation_time")
    if ft_raw is None:
        return None
    if isinstance(ft_raw, str):
        ft = datetime.fromisoformat(ft_raw)
    else:
        ft = ft_raw
    if hasattr(ft, "tzinfo") and ft.tzinfo is None:
        ft = ft.replace(tzinfo=timezone.utc)
    try:
        formation_idx = candles.index.get_indexer(
            [ft], method="ffill",
        )[0]
    except (KeyError, IndexError):
        return None
    if formation_idx < 1:
        return None
    return formation_idx - 1


@register(
    "impulse_body_ratio", strategies=_FVG_STRATEGIES,
    needs_candles=True, dtype="float",
)
def impulse_body_ratio(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Return the impulse candle (C1) body/range ratio."""
    if candles is None:
        return None
    c1_idx = _find_impulse_candle(candles, _meta(signal))
    if c1_idx is None:
        return None
    c1 = candles.iloc[c1_idx]
    range_ = c1["high"] - c1["low"]
    if range_ <= 0:
        return None
    return abs(c1["close"] - c1["open"]) / range_


@register(
    "impulse_size_atr", strategies=_FVG_STRATEGIES,
    needs_candles=True, dtype="float",
)
def impulse_size_atr(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Return the impulse candle (C1) range in pips / ATR-14 in pips."""
    if candles is None:
        return None
    c1_idx = _find_impulse_candle(candles, _meta(signal))
    if c1_idx is None:
        return None
    c1 = candles.iloc[c1_idx]
    c1_range_pips = (c1["high"] - c1["low"]) / pip_size(signal.symbol)
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return c1_range_pips / atr_pips
