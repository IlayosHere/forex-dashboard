"""
strategies/fvg_impulse/data.py
------------------------------
TradingView data-fetching, the FVG dataclass, and FVG lifecycle helpers,
extracted from scanner.py to keep the scanner module under the 200-line limit.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from tvDatafeed import Interval, TvDatafeed

from .config import EXCHANGE_TZ

logger = logging.getLogger(__name__)

_tv: TvDatafeed | None = None


# ---------------------------------------------------------------------------
# TradingView connection
# ---------------------------------------------------------------------------

def get_tv() -> TvDatafeed:
    """Get or create the TvDatafeed connection (lazy singleton)."""
    global _tv
    if _tv is None:
        _tv = TvDatafeed()
        _tv._TvDatafeed__ws_timeout = 15
        logger.info("TvDatafeed connection established")
    return _tv


def reset_tv() -> None:
    """Force reconnection on next call."""
    global _tv
    _tv = None
    logger.warning("TvDatafeed connection reset, will reconnect on next call")


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def get_candles(symbol: str, count: int = 70) -> pd.DataFrame | None:
    """Fetch M15 candles from TradingView. Returns DataFrame or None."""
    df = None
    for attempt in range(2):
        try:
            tv = get_tv()
            df = tv.get_hist(
                symbol=symbol,
                exchange="PEPPERSTONE",
                interval=Interval.in_15_minute,
                n_bars=count,
            )
        except (ConnectionError, TimeoutError, OSError, ValueError) as exc:
            logger.error("TradingView request failed for %s (attempt %d): %s",
                         symbol, attempt + 1, exc)

        if df is not None and not df.empty:
            break

        if attempt == 0:
            reset_tv()
            time.sleep(2)

    if df is None or df.empty:
        logger.error("No data returned for %s", symbol)
        return None

    df = df[["open", "high", "low", "close"]].copy()
    if df.index.tz is None:
        df.index = df.index.tz_localize(EXCHANGE_TZ).tz_convert(timezone.utc)
    else:
        df.index = df.index.tz_convert(timezone.utc)
    return df


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
