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
import os
import threading
import time
from datetime import timezone
from zoneinfo import ZoneInfo

import pandas as pd
from tvDatafeed import Interval, TvDatafeed

__all__ = ["EXCHANGE_TZ", "get_candles", "get_tv", "reset_tv"]

# Broker timezone: tvDatafeed returns naive timestamps in Asia/Jerusalem
# (the machine's local timezone on the production server).
EXCHANGE_TZ = ZoneInfo("Asia/Jerusalem")

logger = logging.getLogger(__name__)

_tv: TvDatafeed | None = None
_tv_lock = threading.Lock()
_tv_token: str | None = None  # cached once at startup, reused on every reconnect

# Global semaphore: caps concurrent TradingView WebSocket requests across all
# threads and callers. TradingView rate-limits aggressive parallel connections
# (HTTP 429). Two concurrent fetches is safe; more risks rejection.
_tv_semaphore = threading.Semaphore(2)

_EXCHANGE = "PEPPERSTONE"
_MAX_ATTEMPTS = 4
_RETRY_SLEEP_SECONDS = 5
_RETRY_BACKOFF_FACTOR = 2   # sleep doubles each attempt: 5s, 10s, 20s
_RATE_LIMIT_SLEEP_SECONDS = 15  # back-off when TV returns 429
_BASE_COLUMNS = ["open", "high", "low", "close"]
_VOLUME_COLUMN = "volume"


# ---------------------------------------------------------------------------
# TradingView connection
# ---------------------------------------------------------------------------

def _get_auth_token() -> str | None:
    """Authenticate once with TV credentials and return the token.

    Called only on first connection. Subsequent reconnects reuse the cached
    token to avoid hitting TradingView's sign-in rate limit.
    """
    import requests as _requests
    username = os.environ.get("TV_USERNAME")
    password = os.environ.get("TV_PASSWORD")
    if not username or not password:
        return None
    try:
        resp = _requests.post(
            "https://www.tradingview.com/accounts/signin/",
            data={"username": username, "password": password, "remember": "on"},
            headers={"Referer": "https://www.tradingview.com"},
            timeout=10,
        )
        token = resp.json().get("user", {}).get("auth_token")
        if token:
            logger.info("TvDatafeed: authenticated successfully")
            return token
        logger.error("TvDatafeed: sign-in response missing token: %s", resp.text[:200])
    except Exception as exc:
        logger.error("TvDatafeed: sign-in request failed: %s", exc)
    return None


def get_tv() -> TvDatafeed:
    """Return the lazy TvDatafeed singleton, creating it on first access.

    On first call, authenticates with TV credentials (if set) and caches the
    token. On reconnect (after reset_tv), reuses the cached token — no
    repeated sign-in calls.
    """
    global _tv, _tv_token
    with _tv_lock:
        if _tv is None:
            if _tv_token is None:
                _tv_token = _get_auth_token()
            if _tv_token:
                _tv = TvDatafeed()
                _tv.token = _tv_token
                logger.info("TvDatafeed connection established (authenticated)")
            else:
                _tv = TvDatafeed()
                logger.warning("TvDatafeed connection established (nologin — set TV_USERNAME/TV_PASSWORD for stability)")
            try:
                _tv._TvDatafeed__ws_timeout = 15
            except AttributeError:
                pass
        return _tv


def reset_tv() -> None:
    """Drop the cached TvDatafeed so the next call reconnects.

    Keeps the cached auth token so reconnects reuse it without re-signing in.
    """
    global _tv
    with _tv_lock:
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
    """Perform a single TvDatafeed fetch, returning None on failure.

    Acquires the global ``_tv_semaphore`` before touching the WebSocket so
    that at most 2 concurrent requests reach TradingView at any time.
    """
    with _tv_semaphore:
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
        except Exception as exc:
            # Catch 429 rate-limit responses and other unexpected errors from
            # the tvDatafeed WebSocket layer.
            if "429" in str(exc):
                logger.warning(
                    "TradingView rate-limited (429) for %s @ %s — "
                    "backing off %ds",
                    symbol, interval, _RATE_LIMIT_SLEEP_SECONDS,
                )
                time.sleep(_RATE_LIMIT_SLEEP_SECONDS)
            else:
                logger.error(
                    "Unexpected TradingView error for %s @ %s: %s",
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
            sleep_seconds = _RETRY_SLEEP_SECONDS * (_RETRY_BACKOFF_FACTOR ** attempt)
            logger.warning(
                "Fetch failed for %s @ %s (attempt %d/%d), retrying in %ds",
                symbol, interval, attempt + 1, _MAX_ATTEMPTS, sleep_seconds,
            )
            reset_tv()
            time.sleep(sleep_seconds)

    if raw is None or raw.empty:
        logger.error("No data returned for %s @ %s", symbol, interval)
        return None

    return _normalize_index(_select_columns(raw))
