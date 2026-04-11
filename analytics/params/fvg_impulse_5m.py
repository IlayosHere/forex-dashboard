"""
analytics/params/fvg_impulse_5m.py
----------------------------------
M5-only FVG-impulse analytics parameters. Registered against
``_FVG_5M_STRATEGIES`` so they are invisible to the M15 variant.
FVG detection reuses ``strategies.fvg_impulse.data`` so the
virginity/consumption rules stay identical to the live scanner.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from analytics.candle_cache import cached_atr, cached_h1
from analytics.params.candle_derived import _analytics_pip_size, _find_signal_bar, _rejection_wick_pips
from analytics.params.fvg_impulse import _FVG_5M_STRATEGIES
from analytics.registry import register
from strategies.fvg_impulse.data import (
    FVG,
    age_and_prune_fvgs,
    detect_fvgs_at_bar,
)

logger = logging.getLogger(__name__)

_VOLATILITY_PERCENTILE_LONG_BARS = 96


@register("h1_fvg_contains_entry", strategies=_FVG_5M_STRATEGIES, needs_candles=True, dtype="bool")
def h1_fvg_contains_entry(signal: Any, candles: pd.DataFrame | None) -> bool | None:
    """Whether the entry price sits inside an active H1 FVG at signal time."""
    if candles is None:
        return None
    h1 = cached_h1(candles)
    idx = _find_signal_bar(h1, signal)
    if idx is None or idx < 2:
        return None
    h = h1["high"].values
    l = h1["low"].values
    c = h1["close"].values
    fvgs: list[FVG] = []
    # Run the full lifecycle (detect + age) up to the bar BEFORE the signal.
    # This matches the M15 scanner's stop-before-signal-bar pattern: aging
    # FVGs through the signal bar itself would kill valid FVGs via the virgin
    # check on the signal bar's wick, even though the entry (close price) may
    # still sit inside the gap.
    for i in range(2, idx):
        detect_fvgs_at_bar(fvgs, h, l, i, h1)
        age_and_prune_fvgs(fvgs, h, l, c, i)
    # Detect any FVG that FORMED at the signal bar (fresh FVGs are not aged
    # by age_and_prune_fvgs on their formation bar, so this is safe).
    if idx >= 2:
        detect_fvgs_at_bar(fvgs, h, l, idx, h1)
    entry = signal.entry
    for fvg in fvgs:
        if not fvg.is_valid:
            continue
        if fvg.bottom <= entry <= fvg.top:
            return True
    return False


@register("volatility_percentile_long", strategies=_FVG_5M_STRATEGIES, needs_candles=True, dtype="float")
def volatility_percentile_long(signal: Any, candles: pd.DataFrame | None) -> float | None:
    """Percentile rank of signal-bar ATR within the prior 96 bars."""
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    atr_series = cached_atr(candles)
    if idx >= len(atr_series):
        return None
    window_start = max(0, idx - (_VOLATILITY_PERCENTILE_LONG_BARS - 1))
    window = atr_series.iloc[window_start:idx + 1].dropna()
    if len(window) < _VOLATILITY_PERCENTILE_LONG_BARS:
        return None
    current = atr_series.iloc[idx]
    if pd.isna(current):
        return None
    count_le = int((window <= current).sum())
    return count_le / len(window) * 100


@register("signal_wick_pips", strategies=_FVG_5M_STRATEGIES, needs_candles=True, dtype="float")
def signal_wick_pips(signal: Any, candles: pd.DataFrame | None) -> float | None:
    """Absolute rejection wick length on the signal bar in raw pips."""
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    bar = candles.iloc[idx]
    pip = _analytics_pip_size(signal.symbol)
    return _rejection_wick_pips(bar, signal.direction, pip)
