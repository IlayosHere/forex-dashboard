"""
analytics/params/structure.py
-----------------------------
Cross-strategy structure & liquidity parameters (themes A-B).

Session timing (``minutes_into_session``, ``hour_bucket``) and liquidity /
HTF position (``dist_to_round_atr``, ``h1_swing_position``,
``bars_since_h1_extreme``). Macro / D1 params live in ``macro.py`` and
regime / momentum / cost params live in ``regime.py``.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from analytics.candle_cache import cached_h1
from analytics.params.candle_derived import _analytics_pip_size, _atr_pips_at_bar, _find_signal_bar
from analytics.params.temporal import _SESSION_RANGES
from analytics.registry import register
from analytics.types import Session

logger = logging.getLogger(__name__)

# Hour-bucket boundaries (UTC hour, inclusive lower bound)
_HOUR_BUCKET_ASIAN_END = 7
_HOUR_BUCKET_LONDON_END = 9
_HOUR_BUCKET_LONDON_NY_END = 16

_ROUND_LEVEL_STEP_PIPS = 50

_H1_SWING_WINDOW = 20
_H1_SWING_NEAR_HIGH = 0.75
_H1_SWING_NEAR_LOW = 0.25

_H1_EXTREME_WINDOW = 48


# ---------------------------------------------------------------------------
# Theme A — Session & timing
# ---------------------------------------------------------------------------

@register("minutes_into_session", dtype="int")
def minutes_into_session(signal: Any, _candles: pd.DataFrame | None) -> int | None:
    """Minutes since the current UTC trading session began.

    HIGH variance risk at current sample sizes — minute-resolution buckets
    spread signals thinly and the CI classifier may not find a stable edge.
    Returns 0 for the ``CLOSE`` session (no meaningful start).
    """
    hour: int = signal.candle_time.hour
    minute: int = signal.candle_time.minute
    for start, end, session in _SESSION_RANGES:
        if start <= hour < end:
            if session is Session.CLOSE:
                return 0
            return int((hour - start) * 60 + minute)
    return 0


@register("hour_bucket", dtype="str")
def hour_bucket(signal: Any, _candles: pd.DataFrame | None) -> str:
    """Coarse 4-bucket UTC-hour classification for cross-strategy reuse."""
    hour: int = signal.candle_time.hour
    if hour < _HOUR_BUCKET_ASIAN_END:
        return "ASIAN_QUIET"
    if hour < _HOUR_BUCKET_LONDON_END:
        return "LONDON_OPEN"
    if hour < _HOUR_BUCKET_LONDON_NY_END:
        return "LONDON_NY"
    return "NY_LATE_CLOSE"


# ---------------------------------------------------------------------------
# Theme B — Liquidity & structure
# ---------------------------------------------------------------------------

@register("dist_to_round_atr", needs_candles=True, dtype="float")
def dist_to_round_atr(signal: Any, candles: pd.DataFrame | None) -> float | None:
    """Distance to the nearest 50-pip round level, normalized by ATR-14."""
    if candles is None:
        return None
    pip = _analytics_pip_size(signal.symbol)
    round_step = _ROUND_LEVEL_STEP_PIPS * pip
    remainder = signal.entry % round_step
    dist_price = min(remainder, round_step - remainder)
    dist_pips = dist_price / pip
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return float(dist_pips / atr_pips)


@register("h1_swing_position", needs_candles=True, dtype="str")
def h1_swing_position(signal: Any, candles: pd.DataFrame | None) -> str | None:
    """Where the signal sits in the last 20 H1 bars: near_high / near_low / mid."""
    if candles is None:
        return None
    h1 = cached_h1(candles)
    idx = _find_signal_bar(h1, signal)
    if idx is None:
        return None
    start = idx - (_H1_SWING_WINDOW - 1)
    if start < 0:
        return None
    window = h1.iloc[start:idx + 1]
    if len(window) < _H1_SWING_WINDOW:
        return None
    rng_high = float(window["high"].max())
    rng_low = float(window["low"].min())
    if rng_high == rng_low:
        return None
    pos = (signal.entry - rng_low) / (rng_high - rng_low)
    if pos >= _H1_SWING_NEAR_HIGH:
        return "near_high"
    if pos <= _H1_SWING_NEAR_LOW:
        return "near_low"
    return "mid"


@register("bars_since_h1_extreme", needs_candles=True, dtype="int")
def bars_since_h1_extreme(signal: Any, candles: pd.DataFrame | None) -> int | None:
    """Bars since the 48-H1-bar window's extreme in the signal direction.

    BUY uses the window min low; SELL uses the window max high.
    """
    if candles is None:
        return None
    h1 = cached_h1(candles)
    idx = _find_signal_bar(h1, signal)
    if idx is None:
        return None
    start = idx - (_H1_EXTREME_WINDOW - 1)
    if start < 0:
        return None
    window = h1.iloc[start:idx + 1]
    if len(window) < _H1_EXTREME_WINDOW:
        return None
    if signal.direction == "BUY":
        extreme_pos = window["low"].idxmin()
    else:
        extreme_pos = window["high"].idxmax()
    extreme_idx = window.index.get_loc(extreme_pos)
    return int(len(window) - 1 - extreme_idx)
