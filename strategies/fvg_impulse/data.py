"""
strategies/fvg_impulse/data.py
------------------------------
FVG dataclass and lifecycle helpers for the M15 FVG-impulse strategy, plus a
thin ``get_candles`` wrapper that delegates to ``shared.market_data`` with the
strategy's native timeframe baked in.

All TvDatafeed connection and retry logic lives in ``shared/market_data.py`` —
see that module for the single source of truth.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import pandas as pd
from tvDatafeed import Interval

from shared.market_data import get_candles as _fetch_candles

logger = logging.getLogger(__name__)

_STRATEGY_INTERVAL: Interval = Interval.in_15_minute


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def get_candles(symbol: str, count: int = 70) -> pd.DataFrame | None:
    """Fetch M15 candles for this strategy via the shared fetcher."""
    return _fetch_candles(symbol, _STRATEGY_INTERVAL, count)


# ---------------------------------------------------------------------------
# FVG data structure
# ---------------------------------------------------------------------------

@dataclass
class FVG:
    """A Fair Value Gap zone."""
    direction: str          # "bullish" or "bearish"
    top: float              # upper boundary
    bottom: float           # lower boundary
    formation_idx: int      # bar index where C2 was (3rd candle)
    formation_time: datetime
    age_bars: int = 0
    is_valid: bool = True

    @property
    def near_edge(self) -> float:
        """Edge price approaches from when retracing."""
        return self.top if self.direction == "bullish" else self.bottom

    @property
    def far_edge(self) -> float:
        """Opposite edge -- SL side."""
        return self.bottom if self.direction == "bullish" else self.top

    @property
    def height(self) -> float:
        """Height of the FVG zone in price units."""
        return self.top - self.bottom


MAX_FVG_AGE = 15  # bars


# ---------------------------------------------------------------------------
# FVG lifecycle helpers
# ---------------------------------------------------------------------------

def detect_fvgs_at_bar(
    fvgs: list[FVG],
    h: Any,
    l: Any,
    i: int,
    candles: pd.DataFrame,
) -> None:
    """Detect new FVGs at bar i (C0=i-2, C1=i-1, C2=i)."""
    c0_high = float(h[i - 2])
    c0_low = float(l[i - 2])
    c2_low = float(l[i])
    c2_high = float(h[i])

    # Bullish FVG: gap above (C0.high < C2.low)
    if c0_high < c2_low:
        fvgs.append(FVG(
            direction="bullish", top=c2_low, bottom=c0_high,
            formation_idx=i,
            formation_time=candles.index[i].to_pydatetime(),
        ))

    # Bearish FVG: gap below (C0.low > C2.high)
    if c0_low > c2_high:
        fvgs.append(FVG(
            direction="bearish", top=c0_low, bottom=c2_high,
            formation_idx=i,
            formation_time=candles.index[i].to_pydatetime(),
        ))


def age_and_prune_fvgs(
    fvgs: list[FVG], h: Any, l: Any, c: Any, i: int,
) -> None:
    """Age, expire, and check virginity/consumption for existing FVGs."""
    for fvg in fvgs:
        if not fvg.is_valid or fvg.formation_idx == i:
            continue

        fvg.age_bars += 1

        if fvg.age_bars > MAX_FVG_AGE:
            fvg.is_valid = False
            continue

        # Close-through consumption: candle closes past far edge
        bar_close = float(c[i])
        if fvg.direction == "bullish" and bar_close < fvg.bottom:
            fvg.is_valid = False
            continue
        if fvg.direction == "bearish" and bar_close > fvg.top:
            fvg.is_valid = False
            continue

        # Virgin check: any touch of near edge kills FVG
        if fvg.direction == "bullish" and float(l[i]) < fvg.near_edge:
            fvg.is_valid = False
            continue
        if fvg.direction == "bearish" and float(h[i]) > fvg.near_edge:
            fvg.is_valid = False
            continue

    # Prune dead FVGs periodically
    if i % 20 == 0:
        fvgs[:] = [f for f in fvgs if f.is_valid]
