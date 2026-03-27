"""
strategies/fvg_impulse/scanner.py - Virgin FVG wick-test scanner.

Fetches 70 M15 candles per symbol, detects FVGs, tracks virginity,
and checks the last closed candle for wick-test rejection signals.

No gates -- bare-bones: virgin FVG + wick into + close outside.

Plugin interface
----------------
scan() -> list[Signal]   ← called by the runner every 15 minutes
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from tvDatafeed import TvDatafeed, Interval

from shared.signal import Signal
from .calculations import calculate_trade_params
from .config import EXCHANGE_TZ

logger = logging.getLogger(__name__)

_tv: TvDatafeed | None = None

# Dedup: set of (symbol, candle_time) to prevent duplicate alerts within a cycle
_alerted_candles: set = set()

MAX_FVG_AGE = 15  # bars

DEFAULT_PAIRS = "EURUSD,AUDUSD,NZDUSD,USDJPY,USDCHF,USDCAD,GBPUSD"


# ---------------------------------------------------------------------------
# TradingView connection
# ---------------------------------------------------------------------------

def _get_tv() -> TvDatafeed:
    """Get or create the TvDatafeed connection (lazy singleton)."""
    global _tv
    if _tv is None:
        _tv = TvDatafeed()
        _tv._TvDatafeed__ws_timeout = 15
        logger.info("TvDatafeed connection established")
    return _tv


def _reset_tv() -> None:
    """Force reconnection on next call."""
    global _tv
    _tv = None
    logger.warning("TvDatafeed connection reset, will reconnect on next call")


# ---------------------------------------------------------------------------
# Data fetching
# ---------------------------------------------------------------------------

def get_candles(symbol: str, count: int = 70) -> Optional[pd.DataFrame]:
    """Fetch M15 candles from TradingView. Returns DataFrame or None."""
    df = None
    for attempt in range(2):
        try:
            tv = _get_tv()
            df = tv.get_hist(
                symbol=symbol,
                exchange="PEPPERSTONE",
                interval=Interval.in_15_minute,
                n_bars=count,
            )
        except Exception as exc:
            logger.error("TradingView request failed for %s (attempt %d): %s",
                         symbol, attempt + 1, exc)

        if df is not None and not df.empty:
            break

        if attempt == 0:
            _reset_tv()
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
        return self.top - self.bottom


# ---------------------------------------------------------------------------
# FVG detection and signal scanning
# ---------------------------------------------------------------------------

def _pip_size(symbol: str) -> float:
    """Return pip size for a symbol."""
    return 0.01 if "JPY" in symbol.upper().replace("/", "") else 0.0001


def _find_last_closed_index(candles: pd.DataFrame) -> Optional[int]:
    """Find index of last closed candle (before current 15-min boundary)."""
    now = datetime.now(timezone.utc)
    current_boundary = now.replace(
        minute=(now.minute // 15) * 15, second=0, microsecond=0,
    )
    for i in range(len(candles) - 1, -1, -1):
        ct = candles.index[i].to_pydatetime()
        if ct < current_boundary:
            return i
    return None


def scan_symbol(candles: pd.DataFrame, symbol: str) -> List[Dict[str, Any]]:
    """Scan one symbol's candles for virgin FVG wick-test signals.

    Rebuilds FVG state from scratch each cycle. Checks only the last
    closed candle for signals.

    Returns list of signal dicts (usually 0 or 1, but a candle can
    wick-test multiple FVGs).
    """
    if len(candles) < 3:
        return []

    last_idx = _find_last_closed_index(candles)
    if last_idx is None or last_idx < 2:
        return []

    # Only alert on fresh candles (closed within last 20 minutes)
    now = datetime.now(timezone.utc)
    candle_time = candles.index[last_idx].to_pydatetime()
    if now - candle_time > timedelta(minutes=20):
        return []

    # Dedup check
    candle_key = (symbol, candle_time)
    if candle_key in _alerted_candles:
        return []

    pip = _pip_size(symbol)
    h = candles["high"].values
    l = candles["low"].values
    c = candles["close"].values
    o = candles["open"].values

    # --- Build FVG list from history (stop BEFORE signal candle) ---
    # The signal candle's wick touches the near edge — that IS the signal.
    # If we process it in the lifecycle loop, the virgin check kills the
    # FVG before we can detect the wick-test.
    fvgs: list[FVG] = []

    for i in range(2, last_idx):
        # Detect new FVGs at bar i (C0=i-2, C1=i-1, C2=i)
        c0_high = float(h[i - 2])
        c0_low = float(l[i - 2])
        c2_low = float(l[i])
        c2_high = float(h[i])

        # Bullish FVG: gap above (C0.high < C2.low)
        if c0_high < c2_low:
            fvgs.append(FVG(
                direction="bullish",
                top=c2_low,
                bottom=c0_high,
                formation_idx=i,
                formation_time=candles.index[i].to_pydatetime(),
            ))

        # Bearish FVG: gap below (C0.low > C2.high)
        if c0_low > c2_high:
            fvgs.append(FVG(
                direction="bearish",
                top=c0_low,
                bottom=c2_high,
                formation_idx=i,
                formation_time=candles.index[i].to_pydatetime(),
            ))

        # Age, expire, and check virginity/consumption for existing FVGs
        for fvg in fvgs:
            if not fvg.is_valid or fvg.formation_idx == i:
                continue

            fvg.age_bars += 1

            # Expire old FVGs
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
            fvgs = [f for f in fvgs if f.is_valid]

    # Also detect FVGs that form on the signal candle itself (they'll
    # have age=0 and be skipped for signals, but will be valid next cycle)
    if last_idx >= 2:
        c0_high = float(h[last_idx - 2])
        c0_low = float(l[last_idx - 2])
        c2_low = float(l[last_idx])
        c2_high = float(h[last_idx])
        if c0_high < c2_low:
            fvgs.append(FVG(
                direction="bullish", top=c2_low, bottom=c0_high,
                formation_idx=last_idx,
                formation_time=candles.index[last_idx].to_pydatetime(),
            ))
        if c0_low > c2_high:
            fvgs.append(FVG(
                direction="bearish", top=c0_low, bottom=c2_high,
                formation_idx=last_idx,
                formation_time=candles.index[last_idx].to_pydatetime(),
            ))

    # --- Check last closed candle for wick-test signals ---
    fvgs = [f for f in fvgs if f.is_valid]
    signals: list[dict] = []
    bar_high = float(h[last_idx])
    bar_low = float(l[last_idx])
    bar_close = float(c[last_idx])
    bar_open = float(o[last_idx])

    for fvg in fvgs:
        if fvg.formation_idx == last_idx:
            continue

        # Wick-test: wick enters zone, close stays outside
        is_test = False
        if fvg.direction == "bullish":
            is_test = bar_low < fvg.near_edge and bar_close > fvg.near_edge
        else:
            is_test = bar_high > fvg.near_edge and bar_close < fvg.near_edge

        if not is_test:
            continue

        direction = "BUY" if fvg.direction == "bullish" else "SELL"
        width_pips = fvg.height / pip

        logger.info(
            "%s FVG signal @ %s: %s near=%.5f far=%.5f width=%.1fpip age=%d",
            direction, candle_time.strftime("%H:%M"), symbol,
            fvg.near_edge, fvg.far_edge, width_pips, fvg.age_bars,
        )

        sig = {
            "symbol": symbol,
            "direction": direction,
            "fvg_near_edge": fvg.near_edge,
            "fvg_far_edge": fvg.far_edge,
            "fvg_width_pips": round(width_pips, 1),
            "fvg_age": fvg.age_bars,
            "fvg_formation_time": fvg.formation_time,
            "candle_time": candle_time,
            "entry_price": bar_close,
            "open": bar_open,
            "high": bar_high,
            "low": bar_low,
            "close": bar_close,
        }
        sig.update(calculate_trade_params(sig))
        signals.append(sig)

    if signals:
        _alerted_candles.add(candle_key)

    return signals


# ---------------------------------------------------------------------------
# Scan all symbols
# ---------------------------------------------------------------------------

def scan_all_symbols(symbols: List[str]) -> List[Dict[str, Any]]:
    """Scan all symbols for virgin FVG wick-test signals."""
    now = datetime.now(timezone.utc)
    _alerted_candles.difference_update(
        {(s, t) for s, t in _alerted_candles if now - t > timedelta(minutes=30)}
    )

    signals: list[dict] = []
    delay = 2  # seconds between TradingView requests

    for i, symbol in enumerate(symbols):
        if i > 0:
            time.sleep(delay)
        candles = get_candles(symbol)
        if candles is None:
            continue

        result = scan_symbol(candles, symbol)
        signals.extend(result)

    return signals


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def _to_signal(raw: Dict[str, Any]) -> Signal:
    """Map a raw signal dict to the shared Signal dataclass."""
    return Signal(
        strategy="fvg-impulse",
        symbol=raw["symbol"],
        direction=raw["direction"],
        candle_time=raw["candle_time"],
        entry=raw["entry_price"],
        sl=raw["sl"],
        tp=raw["tp"],
        lot_size=raw["lot_size"],
        risk_pips=raw["risk_pips"],
        spread_pips=raw["spread_pips"],
        metadata={
            "fvg_near_edge": raw["fvg_near_edge"],
            "fvg_far_edge": raw["fvg_far_edge"],
            "fvg_width_pips": raw["fvg_width_pips"],
            "fvg_age": raw["fvg_age"],
            "fvg_formation_time": raw["fvg_formation_time"].isoformat(),
        },
    )


def scan() -> list[Signal]:
    """Strategy plugin entry point. Called by the runner every 15 minutes.

    Reads FVG_IMPULSE_PAIRS env var (comma-separated) or falls back to
    the 7 major pairs.
    """
    symbols = [
        p.strip()
        for p in os.getenv("FVG_IMPULSE_PAIRS", DEFAULT_PAIRS).split(",")
        if p.strip()
    ]
    raw_signals = scan_all_symbols(symbols)
    return [_to_signal(s) for s in raw_signals]
