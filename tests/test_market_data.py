"""
tests/test_market_data.py
-------------------------
Unit tests for shared/market_data.py: verifies the timeframe-blind fetcher
normalizes the index, preserves volume when present, and passes the caller's
interval through to TvDatafeed. No live network calls — TvDatafeed is mocked.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest
from tvDatafeed import Interval

from shared import market_data


def _raw_df(with_volume: bool, tz: str | None = None) -> pd.DataFrame:
    """Build a fake TvDatafeed response DataFrame."""
    idx = pd.date_range("2025-03-10 00:00", periods=3, freq="15min", tz=tz)
    data = {
        "symbol": ["EURUSD", "EURUSD", "EURUSD"],
        "open":   [1.0800, 1.0805, 1.0810],
        "high":   [1.0810, 1.0815, 1.0820],
        "low":    [1.0795, 1.0800, 1.0805],
        "close":  [1.0805, 1.0810, 1.0815],
    }
    if with_volume:
        data["volume"] = [100.0, 120.0, 110.0]
    return pd.DataFrame(data, index=idx)


@pytest.fixture(autouse=True)
def _reset_tv_singleton() -> None:
    """Clear the module-level singleton between tests."""
    market_data.reset_tv()


def _patch_tv(monkeypatch: pytest.MonkeyPatch, df: pd.DataFrame) -> MagicMock:
    """Install a fake TvDatafeed whose get_hist returns df."""
    fake = MagicMock()
    fake.get_hist.return_value = df
    monkeypatch.setattr(market_data, "get_tv", lambda: fake)
    return fake


def test_get_candles_returns_ohlc_frame(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _patch_tv(monkeypatch, _raw_df(with_volume=False))
    result = market_data.get_candles("EURUSD", Interval.in_15_minute, count=3)
    assert result is not None
    assert list(result.columns) == ["open", "high", "low", "close"]
    assert len(result) == 3
    kwargs = fake.get_hist.call_args.kwargs
    assert kwargs["symbol"] == "EURUSD"
    assert kwargs["interval"] == Interval.in_15_minute
    assert kwargs["n_bars"] == 3


def test_get_candles_preserves_volume_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_tv(monkeypatch, _raw_df(with_volume=True))
    result = market_data.get_candles("EURUSD", Interval.in_5_minute)
    assert result is not None
    assert "volume" in result.columns
    assert list(result.columns) == ["open", "high", "low", "close", "volume"]
    assert result["volume"].iloc[0] == 100.0


def test_get_candles_drops_extra_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extra columns (like 'symbol') should not leak into the result."""
    _patch_tv(monkeypatch, _raw_df(with_volume=False))
    result = market_data.get_candles("EURUSD", Interval.in_15_minute)
    assert result is not None
    assert "symbol" not in result.columns


def test_get_candles_normalizes_naive_index_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A naive index is localized to EXCHANGE_TZ then converted to UTC."""
    _patch_tv(monkeypatch, _raw_df(with_volume=False, tz=None))
    result = market_data.get_candles("EURUSD", Interval.in_15_minute)
    assert result is not None
    assert result.index.tz is not None
    assert str(result.index.tz) == "UTC"


def test_get_candles_normalizes_aware_index_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A tz-aware non-UTC index is converted to UTC."""
    _patch_tv(monkeypatch, _raw_df(with_volume=False, tz="Europe/London"))
    result = market_data.get_candles("EURUSD", Interval.in_15_minute)
    assert result is not None
    assert str(result.index.tz) == "UTC"


def test_get_candles_returns_none_when_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    empty = pd.DataFrame(columns=["open", "high", "low", "close"])
    _patch_tv(monkeypatch, empty)
    result = market_data.get_candles("EURUSD", Interval.in_15_minute)
    assert result is None


def test_get_candles_different_interval_passed_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _patch_tv(monkeypatch, _raw_df(with_volume=False))
    market_data.get_candles("GBPUSD", Interval.in_5_minute, count=50)
    kwargs = fake.get_hist.call_args.kwargs
    assert kwargs["interval"] == Interval.in_5_minute
    assert kwargs["n_bars"] == 50
    assert kwargs["symbol"] == "GBPUSD"
