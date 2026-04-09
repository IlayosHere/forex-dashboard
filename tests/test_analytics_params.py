"""
tests/test_analytics_params.py
-------------------------------
Unit tests for analytics/params/ — temporal, spread, fvg_impulse, nova_candle.
Uses hand-crafted mock signals (no DB needed).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest

from analytics.params.fvg_impulse import fvg_age, fvg_width_pips
from analytics.params.nova_candle import (
    body_pips,
    bos_used,
    candle_efficiency,
    close_wick_ratio,
    spread_tier,
)
from analytics.params.spread import pair_category, spread_risk_ratio
from analytics.params.temporal import day_of_week, session_label


def _signal(
    *,
    hour: int = 10,
    weekday: int = 2,
    spread: float = 1.0,
    risk: float = 10.0,
    symbol: str = "EURUSD",
    direction: str = "BUY",
    metadata: dict[str, Any] | None = None,
) -> MagicMock:
    """Build a minimal mock signal."""
    sig = MagicMock()
    sig.candle_time = datetime(2025, 3, 5 + weekday, hour, 0, tzinfo=timezone.utc)
    sig.spread_pips = spread
    sig.risk_pips = risk
    sig.symbol = symbol
    sig.direction = direction
    sig.signal_metadata = metadata or {}
    return sig


# ---------------------------------------------------------------------------
# temporal.py
# ---------------------------------------------------------------------------


def test_session_label_asian() -> None:
    assert session_label(_signal(hour=3), None) == "ASIAN"


def test_session_label_london() -> None:
    assert session_label(_signal(hour=9), None) == "LONDON"


def test_session_label_ny_overlap() -> None:
    assert session_label(_signal(hour=14), None) == "NY_OVERLAP"


def test_session_label_ny_late() -> None:
    assert session_label(_signal(hour=18), None) == "NY_LATE"


def test_session_label_close() -> None:
    assert session_label(_signal(hour=22), None) == "CLOSE"


def test_day_of_week_wednesday() -> None:
    sig = _signal()
    result = day_of_week(sig, None)
    assert result == sig.candle_time.weekday()


# ---------------------------------------------------------------------------
# spread.py
# ---------------------------------------------------------------------------


def test_spread_risk_ratio_normal() -> None:
    result = spread_risk_ratio(_signal(spread=1.5, risk=15.0), None)
    assert result == pytest.approx(0.1)


def test_spread_risk_ratio_zero_risk() -> None:
    assert spread_risk_ratio(_signal(risk=0.0), None) is None


def test_pair_category_major() -> None:
    assert pair_category(_signal(symbol="EURUSD"), None) == "MAJOR"


def test_pair_category_jpy_cross() -> None:
    assert pair_category(_signal(symbol="EURJPY"), None) == "JPY_CROSS"


def test_pair_category_minor() -> None:
    assert pair_category(_signal(symbol="EURGBP"), None) == "MINOR_CROSS"


# ---------------------------------------------------------------------------
# fvg_impulse.py (metadata-only params)
# ---------------------------------------------------------------------------


def test_fvg_age_from_metadata() -> None:
    sig = _signal(metadata={"fvg_age": 5})
    assert fvg_age(sig, None) == 5


def test_fvg_age_missing() -> None:
    assert fvg_age(_signal(), None) is None


def test_fvg_width_pips_from_metadata() -> None:
    sig = _signal(metadata={"fvg_width_pips": 4.2})
    assert fvg_width_pips(sig, None) == pytest.approx(4.2)


# ---------------------------------------------------------------------------
# nova_candle.py (metadata-only params)
# ---------------------------------------------------------------------------

_NOVA_META: dict[str, Any] = {
    "open": 1.08500,
    "high": 1.08700,
    "low": 1.08500,
    "close": 1.08680,
}


def test_bos_used_true() -> None:
    sig = _signal(metadata={"bos_candle_time": "2025-01-15T12:00:00"})
    assert bos_used(sig, None) is True


def test_bos_used_false() -> None:
    assert bos_used(_signal(metadata={}), None) is False


def test_body_pips_eurusd() -> None:
    sig = _signal(symbol="EURUSD", metadata=_NOVA_META)
    result = body_pips(sig, None)
    expected = abs(1.08680 - 1.08500) / 0.0001
    assert result == pytest.approx(expected, abs=0.1)


def test_body_pips_jpy() -> None:
    meta = {"open": 150.00, "high": 150.50, "low": 150.00, "close": 150.30}
    sig = _signal(symbol="USDJPY", metadata=meta)
    result = body_pips(sig, None)
    assert result == pytest.approx(30.0, abs=0.1)


def test_candle_efficiency() -> None:
    sig = _signal(metadata=_NOVA_META)
    result = candle_efficiency(sig, None)
    body = abs(1.08680 - 1.08500)
    range_ = 1.08700 - 1.08500
    assert result == pytest.approx(body / range_, abs=0.001)


def test_close_wick_ratio_buy() -> None:
    sig = _signal(direction="BUY", metadata=_NOVA_META)
    result = close_wick_ratio(sig, None)
    expected = (1.08700 - 1.08680) / (1.08700 - 1.08500)
    assert result == pytest.approx(expected, abs=0.001)


def test_close_wick_ratio_sell() -> None:
    sig = _signal(direction="SELL", metadata=_NOVA_META)
    result = close_wick_ratio(sig, None)
    expected = (1.08680 - 1.08500) / (1.08700 - 1.08500)
    assert result == pytest.approx(expected, abs=0.001)


def test_spread_tier_h0() -> None:
    # UTC hour 22 + broker offset 2 = broker hour 0
    assert spread_tier(_signal(hour=22), None) == "H0"


def test_spread_tier_h2() -> None:
    assert spread_tier(_signal(hour=10), None) == "H2"


def test_nova_ohlc_missing_returns_none() -> None:
    assert body_pips(_signal(metadata={}), None) is None
    assert candle_efficiency(_signal(metadata={}), None) is None
