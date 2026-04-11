"""
analytics/params/nova_candle.py
-------------------------------
Parameters for the nova-candle strategy.

Nova signals store OHLC in signal_metadata, so body/wick ratios
can be computed without fetching candle data. Candle-dependent params
use the shared ATR helpers.

Additional Nova-only params live in :mod:`analytics.params.nova_candle_v2`
to stay under the 200-effective-line file cap.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from analytics.params.candle_derived import _analytics_pip_size, _atr_pips_at_bar
from analytics.registry import register
from shared.market_data import EXCHANGE_TZ

logger = logging.getLogger(__name__)

_NOVA_STRATEGIES: frozenset[str] = frozenset({"nova-candle"})


def get_ohlc(signal: Any) -> tuple[float, float, float, float] | None:
    """Extract open/high/low/close from signal_metadata."""
    meta: dict[str, Any] = getattr(signal, "signal_metadata", {}) or {}
    try:
        return (
            float(meta["open"]),
            float(meta["high"]),
            float(meta["low"]),
            float(meta["close"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


@register("bos_used", strategies=_NOVA_STRATEGIES, dtype="bool")
def bos_used(signal: Any, _candles: pd.DataFrame | None) -> bool:
    """Return whether a break-of-structure confirmation was used."""
    meta: dict[str, Any] = getattr(signal, "signal_metadata", {}) or {}
    return meta.get("bos_candle_time") is not None


@register("body_pips", strategies=_NOVA_STRATEGIES, dtype="float")
def body_pips(signal: Any, _candles: pd.DataFrame | None) -> float | None:
    """Return the signal candle body size in pips."""
    ohlc = get_ohlc(signal)
    if ohlc is None:
        return None
    open_, _high, _low, close = ohlc
    return abs(close - open_) / _analytics_pip_size(signal.symbol)


@register("candle_efficiency", strategies=_NOVA_STRATEGIES, dtype="float")
def candle_efficiency(signal: Any, _candles: pd.DataFrame | None) -> float | None:
    """Return body / range ratio (0-1); higher means stronger candle."""
    ohlc = get_ohlc(signal)
    if ohlc is None:
        return None
    open_, high, low, close = ohlc
    range_ = high - low
    if range_ <= 0:
        return None
    return abs(close - open_) / range_


@register("close_wick_ratio", strategies=_NOVA_STRATEGIES, dtype="float")
def close_wick_ratio(signal: Any, _candles: pd.DataFrame | None) -> float | None:
    """Return the wick ratio on the close side (rejection wick proportion)."""
    ohlc = get_ohlc(signal)
    if ohlc is None:
        return None
    _open, high, low, close = ohlc
    range_ = high - low
    if range_ <= 0:
        return None
    if signal.direction == "BUY":
        return (high - close) / range_
    return (close - low) / range_


@register("spread_tier", dtype="str")
def spread_tier(signal: Any, _candles: pd.DataFrame | None) -> str:
    """Map candle_time to broker spread tier (H0 / H1 / H2).

    Uses the DST-aware broker timezone rather than a hardcoded UTC offset,
    matching ``strategies/fvg_impulse/calculations.py``. Registered for all
    strategies so every resolved signal carries a tier value.
    """
    broker_hour = signal.candle_time.astimezone(EXCHANGE_TZ).hour
    if broker_hour == 0:
        return "H0"
    if broker_hour == 1:
        return "H1"
    return "H2"


# ---------------------------------------------------------------------------
# Candle-dependent params
# ---------------------------------------------------------------------------

@register(
    "body_atr_ratio", strategies=_NOVA_STRATEGIES,
    needs_candles=True, dtype="float",
)
def body_atr_ratio(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Return signal candle body in pips / ATR-14 in pips."""
    if candles is None:
        return None
    ohlc = get_ohlc(signal)
    if ohlc is None:
        return None
    open_, _high, _low, close = ohlc
    body_pips_val = abs(close - open_) / _analytics_pip_size(signal.symbol)
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return body_pips_val / atr_pips
