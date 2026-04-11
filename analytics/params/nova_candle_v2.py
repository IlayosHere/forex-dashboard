"""
analytics/params/nova_candle_v2.py
----------------------------------
Second batch of Nova-candle analytics parameters.

Split out of :mod:`analytics.params.nova_candle` to keep each file under
the 200-effective-line cap. All params here are Nova-only and registered
with ``_NOVA_STRATEGIES`` so the registry scopes them correctly.

Themes:
  * BOS structural quality — sl_swing_distance_bars, bos_swing_leg_atr
  * Wickless candle precision — open_wick_pips, open_wick_zero
  * Candle anatomy & market context — range_atr_ratio, prior_candle_direction,
    prior_body_atr_ratio, gap_pips
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from analytics.params.candle_derived import (
    _analytics_pip_size,
    _atr_pips_at_bar,
    _find_signal_bar,
    _signal_meta,
)
from analytics.params.nova_candle import _NOVA_STRATEGIES, get_ohlc
from analytics.registry import register

logger = logging.getLogger(__name__)

_DOJI_BODY_PIPS_THRESHOLD = 0.5


def _find_bar_by_time(candles: pd.DataFrame, dt: datetime) -> int | None:
    """Return the ffill index of ``dt`` in the candle DataFrame, or None."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    try:
        idx = candles.index.get_indexer([dt], method="ffill")[0]
        if idx < 0:
            return None
        return int(idx)
    except (KeyError, IndexError):
        return None


# ---------------------------------------------------------------------------
# BOS structural quality
# ---------------------------------------------------------------------------

@register(
    "sl_swing_distance_bars", strategies=_NOVA_STRATEGIES,
    needs_candles=True, dtype="int",
)
def sl_swing_distance_bars(
    signal: Any, candles: pd.DataFrame | None,
) -> int | None:
    """M15 bars between the signal bar and the BOS swing bar.

    Returns None when ``bos_used == False`` (fallback SL path — no real
    swing to measure) or when either bar cannot be located in the window.
    """
    if candles is None:
        return None
    meta = _signal_meta(signal)
    bos_iso = meta.get("bos_candle_time")
    if bos_iso is None:
        return None
    bos_dt = datetime.fromisoformat(bos_iso) if isinstance(bos_iso, str) else bos_iso
    signal_idx = _find_signal_bar(candles, signal)
    if signal_idx is None:
        return None
    bos_idx = _find_bar_by_time(candles, bos_dt)
    if bos_idx is None or bos_idx > signal_idx:
        return None
    return int(signal_idx - bos_idx)


@register(
    "bos_swing_leg_atr", strategies=_NOVA_STRATEGIES,
    needs_candles=True, dtype="float",
)
def bos_swing_leg_atr(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Protected swing leg (entry → BOS swing price) in ATR units."""
    if candles is None:
        return None
    meta = _signal_meta(signal)
    bos_price = meta.get("bos_swing_price")
    if bos_price is None:
        return None
    leg_pips = abs(signal.entry - float(bos_price)) / _analytics_pip_size(signal.symbol)
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return float(leg_pips / atr_pips)


# ---------------------------------------------------------------------------
# Wickless candle precision
# ---------------------------------------------------------------------------

@register("open_wick_pips", strategies=_NOVA_STRATEGIES, dtype="float")
def open_wick_pips(signal: Any, _candles: pd.DataFrame | None) -> float | None:
    """Return the open-side wick in pips (|low-open| BUY, |high-open| SELL)."""
    ohlc = get_ohlc(signal)
    if ohlc is None:
        return None
    open_, high, low, _close = ohlc
    wick = abs(low - open_) if signal.direction == "BUY" else abs(high - open_)
    return float(wick / _analytics_pip_size(signal.symbol))


@register("open_wick_zero", strategies=_NOVA_STRATEGIES, dtype="bool")
def open_wick_zero(signal: Any, _candles: pd.DataFrame | None) -> bool | None:
    """True iff the open-side wick is exactly 0.0 (strict wickless split).

    Variance risk: heavily imbalanced binary — if one bucket dominates
    >95/5 the CI classifier will return ``level="none"``. That is the
    expected outcome, not a bug.
    """
    ohlc = get_ohlc(signal)
    if ohlc is None:
        return None
    open_, high, low, _close = ohlc
    if signal.direction == "BUY":
        return bool(low == open_)
    return bool(high == open_)


# ---------------------------------------------------------------------------
# Candle anatomy & market context
# ---------------------------------------------------------------------------

@register(
    "range_atr_ratio", strategies=_NOVA_STRATEGIES,
    needs_candles=True, dtype="float",
)
def range_atr_ratio(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Signal-candle full range (high-low) in ATR units."""
    if candles is None:
        return None
    ohlc = get_ohlc(signal)
    if ohlc is None:
        return None
    _open, high, low, _close = ohlc
    rng_pips = (high - low) / _analytics_pip_size(signal.symbol)
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return float(rng_pips / atr_pips)


@register(
    "prior_candle_direction", strategies=_NOVA_STRATEGIES,
    needs_candles=True, dtype="str",
)
def prior_candle_direction(
    signal: Any, candles: pd.DataFrame | None,
) -> str | None:
    """Classify prior M15 bar vs signal direction: SAME/OPPOSITE/DOJI."""
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None or idx < 1:
        return None
    prior = candles.iloc[idx - 1]
    body = float(prior["close"]) - float(prior["open"])
    body_pips = abs(body) / _analytics_pip_size(signal.symbol)
    if body_pips < _DOJI_BODY_PIPS_THRESHOLD:
        return "DOJI"
    prior_direction = "BUY" if body > 0 else "SELL"
    return "SAME" if prior_direction == signal.direction else "OPPOSITE"


@register(
    "prior_body_atr_ratio", strategies=_NOVA_STRATEGIES,
    needs_candles=True, dtype="float",
)
def prior_body_atr_ratio(
    signal: Any, candles: pd.DataFrame | None,
) -> float | None:
    """Body of the prior M15 bar in ATR units."""
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None or idx < 1:
        return None
    prior = candles.iloc[idx - 1]
    body_pips = abs(
        float(prior["close"]) - float(prior["open"])
    ) / _analytics_pip_size(signal.symbol)
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return float(body_pips / atr_pips)


@register(
    "gap_pips", strategies=_NOVA_STRATEGIES,
    needs_candles=True, dtype="float",
)
def gap_pips(signal: Any, candles: pd.DataFrame | None) -> float | None:
    """Absolute gap in pips between the signal bar's open and prior close.

    Variance risk: on M15 FX ≥95% of gaps are exactly 0. Acceptable as a
    float; the stats layer handles the long-tail distribution. If the
    post-data run confirms it's always 0, re-bucket into a binary.
    """
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None or idx < 1:
        return None
    signal_open = float(candles.iloc[idx]["open"])
    prior_close = float(candles.iloc[idx - 1]["close"])
    return float(abs(signal_open - prior_close) / _analytics_pip_size(signal.symbol))
