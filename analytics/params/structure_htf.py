"""
analytics/params/structure_htf.py
----------------------------------
Higher-timeframe structure parameters: premium/discount zone relative to prior day range.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from analytics.candle_helpers import cached_d1
from analytics.params.candle_derived import _find_signal_bar
from analytics.registry import register
from shared.calculator import pip_size

logger = logging.getLogger(__name__)

_DISCOUNT_THRESHOLD = 0.33
_PREMIUM_THRESHOLD = 0.67
_MIN_DAY_RANGE_PIPS = 3


def _prior_day_hl(d1: pd.DataFrame, signal: Any) -> tuple[float, float] | None:
    """Return (high, low) of the last completed day before the signal's date.

    Avoids lookahead by excluding the current broker day.
    """
    signal_date = pd.Timestamp(signal.candle_time).tz_convert(d1.index.tz).date()
    prior = d1[d1.index.date < signal_date]
    if prior.empty:
        return None
    last_day = prior.iloc[-1]
    return float(last_day["high"]), float(last_day["low"])


@register("premium_discount_zone", needs_candles=True, dtype="str")
def premium_discount_zone(signal: Any, candles: pd.DataFrame | None) -> str | None:
    """Classify entry as discount / equilibrium / premium vs prior day's range."""
    if candles is None:
        return None
    try:
        d1 = cached_d1(candles)
        if d1.empty:
            return None
        result = _prior_day_hl(d1, signal)
        if result is None:
            return None
        day_high, day_low = result
        day_range = day_high - day_low
        pip = pip_size(signal.symbol)
        if day_range < _MIN_DAY_RANGE_PIPS * pip:
            return None
        pos = (signal.entry - day_low) / day_range
        if pos < _DISCOUNT_THRESHOLD:
            return "discount"
        if pos > _PREMIUM_THRESHOLD:
            return "premium"
        return "equilibrium"
    except Exception:
        return None
