"""
tests/test_analytics_fvg_impulse_5m.py
---------------------------------------
Unit tests for M5-only FVG analytics parameters in
``analytics.params.fvg_impulse_5m``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd

from analytics.params.fvg_impulse_5m import h1_fvg_contains_entry


def _make_h1_candles(
    n: int = 30,
    base_price: float = 1.08,
    start: str = "2025-03-10 00:00",
) -> pd.DataFrame:
    """Build a deterministic H1 OHLC DataFrame (no gaps, all bars identical)."""
    idx = pd.date_range(start, periods=n, freq="1h", tz="UTC")
    data = {
        "open": [base_price] * n,
        "high": [base_price + 0.0010] * n,
        "low": [base_price - 0.0005] * n,
        "close": [base_price + 0.0003] * n,
    }
    return pd.DataFrame(data, index=idx)


def _signal(candle_time: datetime, entry: float = 1.0803) -> MagicMock:
    sig = MagicMock()
    sig.candle_time = candle_time
    sig.symbol = "EURUSD"
    sig.direction = "BUY"
    sig.entry = entry
    sig.risk_pips = 10.0
    sig.spread_pips = 0.5
    sig.signal_metadata = {}
    return sig


def _inject_bullish_fvg(
    df: pd.DataFrame, fvg_bar: int, gap_low: float, gap_high: float,
) -> pd.DataFrame:
    """Inject a bullish FVG at position ``fvg_bar`` (the C2 bar).

    A bullish FVG requires C0.high < C2.low.  We set:
      - C0 (fvg_bar-2) high = gap_low - 0.0001  (below gap bottom)
      - C2 (fvg_bar)   low  = gap_low            (gap bottom)
      - C2 (fvg_bar)   high = gap_high + 0.0010  (above gap top, untouched)

    All subsequent bars are kept below the near_edge (gap_low) so the FVG
    stays virgin until the signal bar.
    """
    df = df.copy()
    # C0 bar: push high below gap
    df.iloc[fvg_bar - 2, df.columns.get_loc("high")] = gap_low - 0.0001
    df.iloc[fvg_bar - 2, df.columns.get_loc("low")] = gap_low - 0.0015

    # C2 bar: set low above C0 high to create the gap
    df.iloc[fvg_bar, df.columns.get_loc("low")] = gap_low
    df.iloc[fvg_bar, df.columns.get_loc("high")] = gap_high + 0.0010
    df.iloc[fvg_bar, df.columns.get_loc("close")] = gap_high + 0.0003

    # Bars after FVG: keep price well below gap near_edge so FVG stays virgin
    for i in range(fvg_bar + 1, len(df)):
        df.iloc[i, df.columns.get_loc("open")] = gap_low - 0.0020
        df.iloc[i, df.columns.get_loc("high")] = gap_low - 0.0001
        df.iloc[i, df.columns.get_loc("low")] = gap_low - 0.0030
        df.iloc[i, df.columns.get_loc("close")] = gap_low - 0.0015

    return df


def test_h1_fvg_contains_entry_uses_h1_max_age() -> None:
    """FVG older than 4 H1 bars (but <15) must be pruned by the H1 max-age fix.

    Setup:
    - 25 H1 bars.
    - Bullish FVG injected at bar 10 (C2).  Gap: 1.0810 – 1.0820.
    - Signal at bar 16 → the FVG is 6 H1 bars old (16 - 10 = 6 > _H1_MAX_FVG_AGE=4).
    - Without the fix (max_age=15) the FVG would still be alive → True.
    - With the fix (max_age=4) the FVG is pruned → False.

    We assert the result is False, confirming the fix is applied.
    """
    gap_low = 1.0810
    gap_high = 1.0820
    # Entry sits inside the gap — would match if FVG were alive.
    entry = (gap_low + gap_high) / 2

    df = _make_h1_candles(n=25, base_price=1.08)
    df = _inject_bullish_fvg(df, fvg_bar=10, gap_low=gap_low, gap_high=gap_high)

    # Signal at bar 16: FVG age = 16 - 10 = 6 H1 bars > _H1_MAX_FVG_AGE (4)
    signal_time = df.index[16].to_pydatetime()
    sig = _signal(candle_time=signal_time, entry=entry)

    # h1_fvg_contains_entry internally resamples candles to H1.
    # We supply H1 candles directly; cached_h1 will resample them to H1
    # (already H1 → same result).
    result = h1_fvg_contains_entry(sig, df)
    assert result is False, (
        "FVG at age 6 H1 bars should be pruned when _H1_MAX_FVG_AGE=4; "
        "got True — the max_age fix is not applied"
    )
