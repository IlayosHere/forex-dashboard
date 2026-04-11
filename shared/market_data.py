"""
shared/market_data.py
---------------------
Timeframe-blind TradingView candle fetcher shared by all strategies and the
analytics engine.

Provides a single ``get_candles`` entry point that takes an explicit ``Interval``
so the same connection logic serves M5, M15, H1, or any other timeframe the
strategies need.

This is the single source of truth for:
  - TvDatafeed connection management (lazy singleton + reset helper)
  - Retry / reconnect policy on fetch failures
  - Timezone normalization (Asia/Jerusalem broker time -> UTC)
  - Column selection (preserves ``volume`` when present)
"""
from __future__ import annotations

import logging
import time
from datetime import timezone

import pandas as pd
from tvDatafeed import Interval, TvDatafeed

from strategies.fvg_impulse.config import EXCHANGE_TZ

__all__ = ["EXCHANGE_TZ", "get_candles", "get_tv", "reset_tv"]

logger = logging.getLogger(__name__)

_tv: TvDatafeed | None = None

_EXCHANGE = "PEPPERSTONE"
_MAX_ATTEMPTS = 2
_RETRY_SLEEP_SECONDS = 2
_BASE_COLUMNS = ["open", "high", "low", "close"]
_VOLUME_COLUMN = "volume"


# ---------------------------------------------------------------------------
# TradingView connection
# ---------------------------------------------------------------------------

def get_tv() -> TvDatafeed:
    """Return the lazy TvDatafeed singleton, creating it on first access."""
    global _tv
    if _tv is None:
        _tv = TvDatafeed()
        _tv._TvDatafeed__ws_timeout = 15
        logger.info("TvDatafeed connection established")
    return _tv


def reset_tv() -> None:
    """Drop the cached TvDatafeed so the next call reconnects."""
    global _tv
    _tv = None
    logger.warning("TvDatafeed connection reset, will reconnect on next call")


# ---------------------------------------------------------------------------
# Candle fetch
# ---------------------------------------------------------------------------

def _select_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Keep OHLC plus volume when the raw response provides it."""
    if _VOLUME_COLUMN in df.columns:
        return df[[*_BASE_COLUMNS, _VOLUME_COLUMN]].copy()
    return df[_BASE_COLUMNS].copy()


def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure the DataFrame has a UTC-tz-aware DatetimeIndex."""
    if df.index.tz is None:
        df.index = df.index.tz_localize(EXCHANGE_TZ).tz_convert(timezone.utc)
    else:
        df.index = df.index.tz_convert(timezone.utc)
    return df


def _fetch_once(
    symbol: str,
    interval: Interval,
    count: int,
) -> pd.DataFrame | None:
    """Perform a single TvDatafeed fetch, returning None on failure."""
    try:
        tv = get_tv()
        return tv.get_hist(
            symbol=symbol,
            exchange=_EXCHANGE,
            interval=interval,
            n_bars=count,
        )
    except (ConnectionError, TimeoutError, OSError, ValueError) as exc:
        logger.error(
            "TradingView request failed for %s @ %s: %s",
            symbol, interval, exc,
        )
        return None


def get_candles(
    symbol: str,
    interval: Interval,
    count: int = 300,
) -> pd.DataFrame | None:
    """Fetch OHLC candles from TradingView for any timeframe.

    Parameters
    ----------
    symbol : str
        Ticker (e.g. ``"EURUSD"``).
    interval : Interval
        TradingView interval enum (``Interval.in_5_minute``, etc.).
    count : int
        Number of most-recent bars to request.

    Returns
    -------
    pd.DataFrame | None
        DataFrame with columns ``[open, high, low, close]`` (plus
        ``volume`` when present in the raw response) and a UTC-tz-aware
        DatetimeIndex. Returns ``None`` when both fetch attempts fail.
    """
    raw: pd.DataFrame | None = None
    for attempt in range(_MAX_ATTEMPTS):
        raw = _fetch_once(symbol, interval, count)
        if raw is not None and not raw.empty:
            break
        if attempt < _MAX_ATTEMPTS - 1:
            reset_tv()
            time.sleep(_RETRY_SLEEP_SECONDS)

    if raw is None or raw.empty:
        logger.error("No data returned for %s @ %s", symbol, interval)
        return None

    return _normalize_index(_select_columns(raw))
