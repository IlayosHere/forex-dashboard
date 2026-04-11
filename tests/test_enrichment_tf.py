"""
tests/test_enrichment_tf.py
---------------------------
Timeframe-aware enrichment tests. Verifies that ``enrich_batch`` routes each
signal's candle lookup through the strategy-specific interval registry so M5
signals never see M15 candles (and vice versa).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import pytest
from tvDatafeed import Interval

from analytics.candle_cache import CandleCache
from analytics.enrichment import enrich_batch
from api.models import SignalModel


def _make_candles(freq: str) -> pd.DataFrame:
    """Return a deterministic OHLC DataFrame at the requested pandas freq."""
    idx = pd.date_range(
        "2025-03-10 00:00", periods=200, freq=freq, tz="UTC",
    )
    base = 1.08
    return pd.DataFrame(
        {
            "open":  [base + i * 0.0001 for i in range(len(idx))],
            "high":  [base + i * 0.0001 + 0.0010 for i in range(len(idx))],
            "low":   [base + i * 0.0001 - 0.0005 for i in range(len(idx))],
            "close": [base + i * 0.0001 + 0.0003 for i in range(len(idx))],
        },
        index=idx,
    )


class _StrategyRecordingStub(CandleCache):
    """Stub that returns a different frame per strategy so enrichment tests
    can assert which TF candles a signal received. It intentionally bypasses
    (symbol, interval) routing — that contract is covered by
    test_candle_cache.py. Here we isolate the enrichment-level contract:
    enrich_batch MUST pass signal.strategy through to the cache.
    """

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple[str, str]] = []
        self.frames: dict[str, pd.DataFrame] = {
            "fvg-impulse":    _make_candles("15min"),
            "fvg-impulse-5m": _make_candles("5min"),
        }

    def get(
        self, symbol: str, strategy: str,
    ) -> pd.DataFrame | None:
        self.calls.append((symbol, strategy))
        return self.frames.get(strategy)


def _signal(strategy: str, candle_time: datetime) -> SignalModel:
    return SignalModel(
        id=str(uuid.uuid4()),
        strategy=strategy,
        symbol="EURUSD",
        direction="BUY",
        candle_time=candle_time,
        entry=1.08500,
        sl=1.08200,
        tp=1.08800,
        lot_size=0.5,
        risk_pips=10.0,
        spread_pips=1.0,
        signal_metadata={},
        created_at=datetime.now(timezone.utc),
        resolution="TP_HIT",
        resolved_at=datetime.now(timezone.utc),
        resolved_price=1.08800,
        resolution_candles=5,
    )


def test_enrich_batch_passes_strategy_to_cache() -> None:
    cache = _StrategyRecordingStub()
    signals: list[Any] = [
        _signal("fvg-impulse", datetime(2025, 3, 10, 2, 0, tzinfo=timezone.utc)),
        _signal(
            "fvg-impulse-5m", datetime(2025, 3, 10, 2, 5, tzinfo=timezone.utc),
        ),
    ]

    enriched = enrich_batch(signals, candle_cache=cache)

    assert len(enriched) == 2
    assert ("EURUSD", "fvg-impulse") in cache.calls
    assert ("EURUSD", "fvg-impulse-5m") in cache.calls


def test_enrich_batch_m5_signal_receives_m5_candles() -> None:
    """An M5 signal must not be enriched with M15 candles."""
    cache = _StrategyRecordingStub()
    m5_frame = cache.frames["fvg-impulse-5m"]
    m15_frame = cache.frames["fvg-impulse"]

    # Sanity: the two frames have distinct bar cadences
    assert m5_frame.index[1] - m5_frame.index[0] == pd.Timedelta(minutes=5)
    assert m15_frame.index[1] - m15_frame.index[0] == pd.Timedelta(minutes=15)

    sig = _signal(
        "fvg-impulse-5m", datetime(2025, 3, 10, 1, 0, tzinfo=timezone.utc),
    )
    enrich_batch([sig], candle_cache=cache)
    assert cache.calls == [("EURUSD", "fvg-impulse-5m")]


def test_unknown_strategy_defaults_to_m15() -> None:
    from analytics.candle_cache import STRATEGY_INTERVALS, interval_for_strategy

    assert interval_for_strategy("brand-new-h1-strategy") == Interval.in_15_minute
    assert all(isinstance(v, Interval) for v in STRATEGY_INTERVALS.values())


def test_strategy_intervals_match_scanner_declarations() -> None:
    """Registry and scanner-declared TFs must agree.

    Every scanner that imports `shared.market_data.get_candles` picks its own
    Interval. If a scanner updates its native TF, `STRATEGY_INTERVALS` must
    update too — otherwise the analytics pipeline silently enriches against
    the wrong timeframe. This test is the canary.
    """
    from analytics.candle_cache import STRATEGY_INTERVALS
    from strategies.nova_candle import scanner as nova_scanner

    assert (
        STRATEGY_INTERVALS["nova-candle"] == nova_scanner._STRATEGY_INTERVAL
    ), (
        "STRATEGY_INTERVALS['nova-candle'] is out of sync with "
        "strategies/nova_candle/scanner.py::_STRATEGY_INTERVAL"
    )
