"""
analytics/params/macro.py
-------------------------
Cross-strategy daily / macro parameters.

Broker-day range position, prior-day H/L distance, and D1 trend — all use
the shared ``cached_d1`` resample to minimize work across signals that
share the same underlying candle DataFrame.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from analytics.candle_cache import cached_atr, cached_d1
from analytics.params.candle_derived import _analytics_pip_size, _atr_pips_at_bar, _find_signal_bar
from analytics.registry import register
from shared.market_data import EXCHANGE_TZ

logger = logging.getLogger(__name__)

_D1_MIN_RANGE_PIPS = 3.0
_D1_POS_LOW = 0.2
_D1_POS_MID_LOW = 0.4
_D1_POS_MID = 0.6
_D1_POS_MID_HIGH = 0.8

_D1_TREND_LOOKBACK = 5
_D1_TREND_FLAT_THRESHOLD = 0.5
# ATR-5 on D1 matches the 5-day lookback. ATR-14 would need 14 D1 bars of
# history, but the M15 candle cache only covers ~5 days → ATR-14 on D1 is
# always NaN in practice. ATR-5 needs exactly 5 D1 bars, which we reliably
# have whenever the 5-bar trend computation itself has enough data.
_D1_ATR_PERIOD = 5


def _day_start_utc(signal: Any) -> pd.Timestamp:
    """Return the signal's broker-day start as a UTC ``pd.Timestamp``."""
    broker_now = signal.candle_time.astimezone(EXCHANGE_TZ)
    day_start_broker = broker_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return pd.Timestamp(day_start_broker).tz_convert("UTC")


@register("htf_range_position_d1", needs_candles=True, dtype="str")
def htf_range_position_d1(signal: Any, candles: pd.DataFrame | None) -> str | None:
    """Position of entry within the broker-day's so-far range (5 buckets).

    Day range is computed from the intraday slice ending at the signal bar,
    so there's no outcome leakage from later bars.
    """
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    day_start_utc = _day_start_utc(signal)
    signal_bar_ts = candles.index[idx]
    intraday = candles.loc[day_start_utc:signal_bar_ts]
    if len(intraday) < 1:
        return None
    day_high = float(intraday["high"].max())
    day_low = float(intraday["low"].min())
    day_range = day_high - day_low
    pip = _analytics_pip_size(signal.symbol)
    if day_range / pip < _D1_MIN_RANGE_PIPS:
        return None
    pos = (signal.entry - day_low) / day_range
    if pos < _D1_POS_LOW:
        return "LOW"
    if pos < _D1_POS_MID_LOW:
        return "MID_LOW"
    if pos < _D1_POS_MID:
        return "MID"
    if pos < _D1_POS_MID_HIGH:
        return "MID_HIGH"
    return "HIGH"


@register("dist_to_prior_day_hl_atr", needs_candles=True, dtype="float")
def dist_to_prior_day_hl_atr(signal: Any, candles: pd.DataFrame | None) -> float | None:
    """Distance from entry to the nearest prior-day H/L, normalized by ATR-14."""
    if candles is None:
        return None
    d1 = cached_d1(candles)
    day_start_utc = _day_start_utc(signal)
    prior = d1.loc[d1.index < day_start_utc]
    if len(prior) == 0:
        return None
    last_prior = prior.iloc[-1]
    pip = _analytics_pip_size(signal.symbol)
    dist_to_high = abs(signal.entry - float(last_prior["high"])) / pip
    dist_to_low = abs(signal.entry - float(last_prior["low"])) / pip
    dist_pips = min(dist_to_high, dist_to_low)
    atr_pips = _atr_pips_at_bar(candles, signal)
    if atr_pips is None or atr_pips == 0:
        return None
    return float(dist_pips / atr_pips)


@register("d1_trend", needs_candles=True, dtype="str")
def d1_trend(signal: Any, candles: pd.DataFrame | None) -> str | None:
    """D1 trend bucket (up / down / flat) from the prior 5 completed D1 bars.

    The 5-bar close-to-close delta is compared against D1 ATR-14; anything
    under half an ATR is "flat".
    """
    if candles is None:
        return None
    d1 = cached_d1(candles)
    day_start_utc = _day_start_utc(signal)
    d1_prior = d1.loc[d1.index < day_start_utc]
    if len(d1_prior) < _D1_TREND_LOOKBACK:
        return None
    last_bars = d1_prior.iloc[-_D1_TREND_LOOKBACK:]
    delta = float(last_bars["close"].iloc[-1] - last_bars["close"].iloc[0])
    d1_atr_series = cached_atr(d1, period=_D1_ATR_PERIOD)
    if len(d1_atr_series) == 0:
        return None
    atr_at_prior = d1_atr_series.iloc[len(d1_prior) - 1]
    if pd.isna(atr_at_prior):
        return None
    d1_atr = float(atr_at_prior)
    if d1_atr == 0:
        return None
    normalized = abs(delta) / d1_atr
    if normalized < _D1_TREND_FLAT_THRESHOLD:
        return "flat"
    return "up" if delta > 0 else "down"
