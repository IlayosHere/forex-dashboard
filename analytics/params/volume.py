"""
analytics/params/volume.py
--------------------------
Session-normalised volume parameter for all strategies.

Uses TradingView tick count as an activity proxy — FX has no central exchange
volume. The single ``volume_regime`` param compares signal-bar volume only
against bars from the same session window (Asian / London / NY) so that the
natural session-volume difference (NY > Asian) does not dominate the bucket.
"""
from __future__ import annotations

import logging
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from analytics.params.candle_derived import _find_signal_bar, _volume_at_bar
from analytics.registry import register

logger = logging.getLogger(__name__)

_NY_TZ = ZoneInfo("America/New_York")
_VOL_REGIME_LOW = 0.7
_VOL_REGIME_HIGH = 1.5
_VOL_BASELINE_BARS = 50
_VOL_MIN_SESSION_BARS = 10


def _session_for_ny_hour(hour: int) -> str:
    """Map a NY-local hour (0-23) to a session group name."""
    if 7 <= hour <= 12:
        return "london"
    if 13 <= hour <= 20:
        return "ny"
    return "asian"


def _session_bar_volumes(
    candles: pd.DataFrame,
    idx: int,
    session: str,
) -> pd.Series:
    """Return volume series for the prior 50 bars filtered to ``session``.

    Falls back to all prior 50 bars when fewer than _VOL_MIN_SESSION_BARS
    same-session bars are found.
    """
    prior = candles["volume"].iloc[max(0, idx - _VOL_BASELINE_BARS):idx]
    if len(prior) == 0:
        return prior
    ny_hours = prior.index.tz_convert(_NY_TZ).hour
    mask = pd.Series(ny_hours, index=prior.index).map(_session_for_ny_hour) == session
    session_bars = prior[mask.values]
    if len(session_bars) >= _VOL_MIN_SESSION_BARS:
        return session_bars
    return prior


@register("volume_regime", needs_candles=True, dtype="str")
def volume_regime(
    signal: Any,
    candles: pd.DataFrame | None,
) -> str | None:
    """Session-normalized volume regime at the signal bar.

    Compares signal-bar tick count to the mean volume of prior bars in the
    same session window (Asian / London / NY). Falls back to all prior 50
    bars when fewer than 10 same-session bars exist in the window.
    Returns None when volume data is unavailable or history is insufficient.
    """
    if candles is None:
        return None
    if "volume" not in candles.columns:
        return None
    bar_volume = _volume_at_bar(candles, signal)
    if bar_volume is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None or idx < 1:
        return None
    ct = signal.candle_time
    if hasattr(ct, "tzinfo") and ct.tzinfo is None:
        from datetime import timezone
        ct = ct.replace(tzinfo=timezone.utc)
    ny_hour = ct.astimezone(_NY_TZ).hour
    session = _session_for_ny_hour(ny_hour)
    baseline = _session_bar_volumes(candles, idx, session)
    if baseline.isna().any() or len(baseline) == 0:
        return None
    mean_vol = float(baseline.mean())
    if mean_vol <= 0:
        return None
    rv = bar_volume / mean_vol
    if rv < _VOL_REGIME_LOW:
        return "low"
    if rv > _VOL_REGIME_HIGH:
        return "high"
    return "normal"
