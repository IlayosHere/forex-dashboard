"""
tests/test_resolver.py
-----------------------
Tests for runner/resolver.py: resolution helpers, nova two-phase logic,
and the resolve_pending_signals public API.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pandas as pd
import pytest
from sqlalchemy.orm import Session

from api.models import SignalModel
from runner.resolver import (
    NOVA_FILL_CANDLES,
    _bars_needed,
    _check_bar,
    _check_fill,
    _resolve_nova,
    _resolve_price,
    _resolve_signal,
    _signal_candle_idx,
    resolve_pending_signals,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
_NEUTRAL = {"high": 1.0870, "low": 1.0851, "close": 1.0860}  # no BUY fill, no SL/TP
_FILL_BAR = {"high": 1.0870, "low": 1.0840, "close": 1.0855}  # BUY fill (low <= 1.085)


def _idx(n: int, start: datetime = _T0) -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="15min", tz=timezone.utc)


def _df(bars: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "high": [b["high"] for b in bars],
            "low": [b["low"] for b in bars],
            "close": [b["close"] for b in bars],
        },
        index=_idx(len(bars)),
    )


def _signal(
    *,
    strategy: str = "fvg-impulse",
    direction: str = "BUY",
    candle_time: datetime = _T0,
    entry: float = 1.0850,
    sl: float = 1.0820,
    tp: float = 1.0910,
) -> SignalModel:
    return SignalModel(
        id=str(uuid.uuid4()),
        strategy=strategy,
        symbol="EURUSD",
        direction=direction,
        candle_time=candle_time,
        entry=entry,
        sl=sl,
        tp=tp,
        lot_size=0.5,
        risk_pips=30.0,
        spread_pips=1.2,
        signal_metadata={},
        created_at=datetime.now(timezone.utc),
    )


def _persist(db: Session, sig: SignalModel) -> SignalModel:
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig


# ---------------------------------------------------------------------------
# _bars_needed
# ---------------------------------------------------------------------------


def test_bars_needed_caps_at_500() -> None:
    sig = _signal(candle_time=datetime(2023, 1, 1, tzinfo=timezone.utc))
    assert _bars_needed([sig]) == 500


def test_bars_needed_one_hour_old() -> None:
    fake_now = datetime(2025, 6, 1, 14, 0, tzinfo=timezone.utc)
    sig = _signal(candle_time=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc))
    with patch("runner.resolver.datetime") as m:
        m.now.return_value = fake_now
        result = _bars_needed([sig])
    assert result == 110  # ceil(3600 / 900) = 4 candles; 4 + 96 + 10 = 110


def test_bars_needed_uses_oldest_signal() -> None:
    recent = _signal(candle_time=datetime(2025, 6, 1, 13, 0, tzinfo=timezone.utc))
    old = _signal(candle_time=datetime(2023, 1, 1, tzinfo=timezone.utc))
    assert _bars_needed([recent, old]) == 500


# ---------------------------------------------------------------------------
# _signal_candle_idx
# ---------------------------------------------------------------------------


def test_signal_candle_idx_exact_match() -> None:
    df = pd.DataFrame({"high": [1.09], "low": [1.08], "close": [1.085]}, index=_idx(1))
    assert _signal_candle_idx(df, _T0) == 0


def test_signal_candle_idx_after_all_rows_returns_none() -> None:
    df = pd.DataFrame({"high": [1.09], "low": [1.08], "close": [1.085]}, index=_idx(1))
    assert _signal_candle_idx(df, _T0 + timedelta(hours=10)) is None


def test_signal_candle_idx_naive_datetime() -> None:
    df = pd.DataFrame({"high": [1.09], "low": [1.08], "close": [1.085]}, index=_idx(1))
    naive = datetime(2025, 6, 1, 12, 0)  # same as _T0 but no tzinfo
    assert _signal_candle_idx(df, naive) == 0


# ---------------------------------------------------------------------------
# _check_bar
# ---------------------------------------------------------------------------


def test_check_bar_buy_tp_hit() -> None:
    assert _check_bar(_signal(direction="BUY"), 1.0920, 1.0840) == "TP_HIT"


def test_check_bar_buy_sl_hit() -> None:
    assert _check_bar(_signal(direction="BUY"), 1.0870, 1.0815) == "SL_HIT"


def test_check_bar_buy_both_sl_wins() -> None:
    assert _check_bar(_signal(direction="BUY"), 1.0920, 1.0815) == "SL_HIT"


def test_check_bar_buy_no_hit() -> None:
    assert _check_bar(_signal(direction="BUY"), 1.0880, 1.0840) is None


def test_check_bar_sell_tp_hit() -> None:
    sig = _signal(direction="SELL", sl=1.0910, tp=1.0820)
    assert _check_bar(sig, 1.0870, 1.0815) == "TP_HIT"  # low <= tp


def test_check_bar_sell_sl_hit() -> None:
    sig = _signal(direction="SELL", sl=1.0910, tp=1.0820)
    assert _check_bar(sig, 1.0915, 1.0840) == "SL_HIT"  # high >= sl


# ---------------------------------------------------------------------------
# _resolve_price
# ---------------------------------------------------------------------------


def test_resolve_price_tp_hit() -> None:
    assert _resolve_price(_signal(), "TP_HIT", 1.0895) == pytest.approx(1.0910)


def test_resolve_price_sl_hit() -> None:
    assert _resolve_price(_signal(), "SL_HIT", 1.0840) == pytest.approx(1.0820)


def test_resolve_price_expired_uses_close() -> None:
    assert _resolve_price(_signal(), "EXPIRED", 1.0855) == pytest.approx(1.0855)


# ---------------------------------------------------------------------------
# _check_fill
# ---------------------------------------------------------------------------


def test_check_fill_buy_reached() -> None:
    assert _check_fill(_signal(direction="BUY", entry=1.0850), 1.0870, 1.0840) is True


def test_check_fill_buy_not_reached() -> None:
    assert _check_fill(_signal(direction="BUY", entry=1.0850), 1.0870, 1.0860) is False


def test_check_fill_sell_reached() -> None:
    assert _check_fill(_signal(direction="SELL", entry=1.0850), 1.0850, 1.0830) is True


# ---------------------------------------------------------------------------
# _resolve_nova
# ---------------------------------------------------------------------------


def test_resolve_nova_tp_hit_after_fill() -> None:
    sig = _signal(strategy="nova-candle")
    bars = [
        _NEUTRAL,                                              # idx 0 — signal candle
        _FILL_BAR,                                             # idx 1 — fill (low <= 1.085)
        {"high": 1.0920, "low": 1.0860, "close": 1.0915},    # idx 2 — TP hit
    ]
    assert _resolve_nova(sig, _df(bars), start_idx=0) is True
    assert sig.resolution == "TP_HIT"
    assert sig.resolved_price == pytest.approx(1.0910)
    assert sig.resolution_candles == 2  # counted from start_idx


def test_resolve_nova_not_filled() -> None:
    sig = _signal(strategy="nova-candle")
    bars = [_NEUTRAL] * (NOVA_FILL_CANDLES + 1)
    assert _resolve_nova(sig, _df(bars), start_idx=0) is True
    assert sig.resolution == "NOT_FILLED"
    assert sig.resolution_candles == NOVA_FILL_CANDLES


def test_resolve_nova_fill_window_not_closed_returns_false() -> None:
    sig = _signal(strategy="nova-candle")
    bars = [_NEUTRAL] * 3  # only 2 bars after start_idx=0, window needs 10
    assert _resolve_nova(sig, _df(bars), start_idx=0) is False
    assert sig.resolution is None


def test_resolve_nova_expired_after_tp_sl_window() -> None:
    sig = _signal(strategy="nova-candle")
    with patch("runner.resolver.MAX_RESOLUTION_CANDLES", 3):
        bars = [_NEUTRAL, _FILL_BAR] + [_NEUTRAL] * 3
        assert _resolve_nova(sig, _df(bars), start_idx=0) is True
    assert sig.resolution == "EXPIRED"


# ---------------------------------------------------------------------------
# _resolve_signal — standard (non-nova)
# ---------------------------------------------------------------------------


def test_resolve_signal_buy_tp_hit() -> None:
    sig = _signal(direction="BUY")
    bars = [_NEUTRAL, {"high": 1.0920, "low": 1.0860, "close": 1.0915}]
    assert _resolve_signal(sig, _df(bars)) is True
    assert sig.resolution == "TP_HIT"
    assert sig.resolution_candles == 1


def test_resolve_signal_sell_sl_hit() -> None:
    sig = _signal(direction="SELL", sl=1.0910, tp=1.0820)
    bars = [_NEUTRAL, {"high": 1.0915, "low": 1.0860, "close": 1.0880}]
    assert _resolve_signal(sig, _df(bars)) is True
    assert sig.resolution == "SL_HIT"


def test_resolve_signal_expired() -> None:
    sig = _signal(direction="BUY")
    with patch("runner.resolver.MAX_RESOLUTION_CANDLES", 3):
        assert _resolve_signal(sig, _df([_NEUTRAL] * 5)) is True
    assert sig.resolution == "EXPIRED"


def test_resolve_signal_not_enough_candles_returns_false() -> None:
    sig = _signal(direction="BUY")
    with patch("runner.resolver.MAX_RESOLUTION_CANDLES", 5):
        assert _resolve_signal(sig, _df([_NEUTRAL] * 2)) is False
    assert sig.resolution is None


def test_resolve_signal_candle_not_in_df_returns_false() -> None:
    sig = _signal(candle_time=datetime(2099, 1, 1, tzinfo=timezone.utc))
    assert _resolve_signal(sig, _df([_NEUTRAL] * 3)) is False


def test_resolve_signal_nova_delegates_fill_check() -> None:
    sig = _signal(strategy="nova-candle")
    bars = [_NEUTRAL] * (NOVA_FILL_CANDLES + 1)
    assert _resolve_signal(sig, _df(bars)) is True
    assert sig.resolution == "NOT_FILLED"


# ---------------------------------------------------------------------------
# resolve_pending_signals
# ---------------------------------------------------------------------------


def test_resolve_pending_no_signals_returns_zero(db: Session) -> None:
    assert resolve_pending_signals(db) == 0


def test_resolve_pending_skips_already_resolved(db: Session) -> None:
    sig = _persist(db, _signal())
    sig.resolution = "TP_HIT"
    db.commit()
    with patch("runner.resolver.get_candles") as mock_gc:
        assert resolve_pending_signals(db) == 0
    mock_gc.assert_not_called()


def test_resolve_pending_skips_when_no_candle_data(db: Session) -> None:
    _persist(db, _signal())
    with patch("runner.resolver.get_candles", return_value=None):
        assert resolve_pending_signals(db) == 0


def test_resolve_pending_resolves_one_signal(db: Session) -> None:
    sig = _persist(db, _signal())
    tp_df = _df([
        _NEUTRAL,
        {"high": 1.0920, "low": 1.0860, "close": 1.0915},    # TP hit
    ])
    with patch("runner.resolver.get_candles", return_value=tp_df):
        result = resolve_pending_signals(db)
    assert result == 1
    db.refresh(sig)
    assert sig.resolution == "TP_HIT"
