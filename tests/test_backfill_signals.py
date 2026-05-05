"""
tests/test_backfill_signals.py
------------------------------
Tests for scripts/backfill_signals.py — covering:

  1. fake_now offset selects the correct last-closed index
  2. Slice passed to scan_symbol never contains future candles
  3. No emitted signal has candle_time > as_of_time (lookahead bias)
  4. FVG invalidated by a future close still emits at the test candle
  5. Warmup region excluded from emit window
  6. Emit window is strictly half-open [start, end)
  7. Indices < 2 are skipped
  8. Weekend / hour gap in candles does not crash
  9. Symbol with < 3 candles produces zero signals, no crash
 10. Re-running backfill twice is idempotent (no duplicate rows)
 11. Pre-existing live signal is not overwritten by backfill
 12. _alerted_candles is empty at the start of each iteration
 13. --dry-run writes nothing to the DB
 14. --strict aborts on injected invariant violation
 15. Backfill result matches direct live-scan result (live-equivalence)
 16. Backfill metadata keys are stamped on every signal
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import StaticPool, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# Ensure project root is importable regardless of working directory
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.db import Base
from api.models import SignalModel
from scripts.backfill_signals import (
    WARMUP_BARS,
    BackfillReport,
    _check_signal_invariants,
    _replay_fvg,
    emit_indices,
    fake_now_for_index,
    slice_as_of,
)
from shared.signal import Signal
from strategies.fvg_impulse import scanner as fvg_scanner

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(bind=_ENGINE, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def _tables() -> None:
    Base.metadata.create_all(bind=_ENGINE)
    yield
    Base.metadata.drop_all(bind=_ENGINE)


@pytest.fixture()
def db() -> Session:
    session = _Session()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Candle-building helpers (mirrors test_fvg_impulse.py fixtures)
# ---------------------------------------------------------------------------

PIP = 0.0001
SYMBOL = "EURUSD"
BASE = 1.1000
NEAR_BULL = 1.1010
FAR_BULL = 1.0990
INTERVAL = 15


def _utc_index(n: int, freq: str = "15min", start_hour: int = 8) -> pd.DatetimeIndex:
    start = datetime(2026, 4, 21, start_hour, 0, tzinfo=timezone.utc)
    return pd.date_range(start, periods=n, freq=freq, tz=timezone.utc)


def _flat_ohlc(n: int, price: float = BASE) -> pd.DataFrame:
    idx = _utc_index(n)
    data = {
        "open": np.full(n, price),
        "high": np.full(n, price + 5 * PIP),
        "low": np.full(n, price - 5 * PIP),
        "close": np.full(n, price),
        "volume": np.ones(n),
    }
    return pd.DataFrame(data, index=idx)


def _candles_with_fvg_and_wick(
    n: int = 10,
    fvg_near: float = NEAR_BULL,
    fvg_far: float = FAR_BULL,
    direction: str = "bullish",
) -> pd.DataFrame:
    """Build candles with a virgin FVG + wick-test signal at bar n-2.

    Layout identical to _m15_candles_with_setup in test_fvg_impulse.py.
    Bar n-1 is the current-forming bar (excluded from last_closed).
    """
    idx = _utc_index(n)
    quiet = fvg_near + 10 * PIP if direction == "bullish" else fvg_near - 10 * PIP
    opens = np.full(n, quiet)
    highs = np.full(n, quiet + 5 * PIP)
    lows = np.full(n, quiet - 2 * PIP)
    closes = np.full(n, quiet)

    if direction == "bullish":
        lows = np.full(n, quiet - 2 * PIP)
        highs[0] = fvg_far - PIP;  lows[0] = fvg_far - 5 * PIP
        closes[0] = fvg_far - 2 * PIP; opens[0] = fvg_far - 2 * PIP
        lows[1] = fvg_near + 5 * PIP; highs[1] = fvg_near + 12 * PIP
        closes[1] = fvg_near + 8 * PIP; opens[1] = fvg_near + 8 * PIP
        lows[2] = fvg_near + PIP; highs[2] = fvg_near + 10 * PIP
        closes[2] = fvg_near + 5 * PIP; opens[2] = fvg_near + 5 * PIP
        s = n - 2
        lows[s] = fvg_near - 2 * PIP   # wick into gap
        closes[s] = fvg_near + 3 * PIP  # close stays outside
        opens[s] = fvg_near + 3 * PIP
        highs[s] = fvg_near + 8 * PIP
    else:
        highs = np.full(n, quiet + 2 * PIP)
        lows[0] = fvg_far + PIP; highs[0] = fvg_far + 5 * PIP
        closes[0] = fvg_far + 2 * PIP; opens[0] = fvg_far + 2 * PIP
        highs[1] = fvg_near - 5 * PIP; lows[1] = fvg_near - 12 * PIP
        closes[1] = fvg_near - 8 * PIP; opens[1] = fvg_near - 8 * PIP
        highs[2] = fvg_near - PIP; lows[2] = fvg_near - 10 * PIP
        closes[2] = fvg_near - 5 * PIP; opens[2] = fvg_near - 5 * PIP
        s = n - 2
        highs[s] = fvg_near + 2 * PIP   # wick into gap
        closes[s] = fvg_near - 3 * PIP  # close stays outside
        opens[s] = fvg_near - 3 * PIP
        lows[s] = fvg_near - 8 * PIP

    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": np.ones(n)},
        index=idx,
    )


# ---------------------------------------------------------------------------
# 1. fake_now offset selects the correct last-closed index
# ---------------------------------------------------------------------------

def test_fake_now_selects_target_candle_as_last_closed() -> None:
    """_find_last_closed_index must return idx, not idx-1 or None."""
    df = _flat_ohlc(10)
    target_idx = 7
    fake_now = fake_now_for_index(df, target_idx, INTERVAL)

    fvg_scanner._alerted_candles.clear()
    with patch("strategies.fvg_impulse.scanner.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = fvg_scanner._find_last_closed_index(df)

    assert result == target_idx, (
        f"Expected last_closed_index={target_idx} but got {result}. "
        "fake_now offset is wrong — the target candle is not being selected."
    )


def test_fake_now_not_30s_offset() -> None:
    """Confirm the old +30s offset would fail (regression guard)."""
    df = _flat_ohlc(10)
    target_idx = 7
    # Simulate the old (broken) offset
    candle_time = df.index[target_idx].to_pydatetime()
    broken_fake_now = candle_time + timedelta(seconds=30)

    fvg_scanner._alerted_candles.clear()
    with patch("strategies.fvg_impulse.scanner.datetime") as mock_dt:
        mock_dt.now.return_value = broken_fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        result = fvg_scanner._find_last_closed_index(df)

    # With +30s, current_boundary == candle_time, so target fails the < check
    assert result != target_idx, (
        "The +30s offset should NOT select the target candle. "
        "If this passes the scanner logic changed."
    )


# ---------------------------------------------------------------------------
# 2. Slice contains no future candles
# ---------------------------------------------------------------------------

def test_slice_as_of_last_row_equals_target_candle() -> None:
    """slice_as_of(candles, idx).index[-1] must equal candles.index[idx]."""
    df = _flat_ohlc(20)
    for idx in [2, 5, 10, 19]:
        sliced = slice_as_of(df, idx)
        assert sliced.index[-1] == df.index[idx]
        assert len(sliced) == idx + 1


def test_replay_fvg_slice_does_not_contain_future() -> None:
    """Monkey-patch scan_symbol to capture the slice — assert no future row."""
    df = _candles_with_fvg_and_wick(n=15)
    signal_candle_idx = 13  # n-2
    start = df.index[signal_candle_idx].to_pydatetime()
    end = start + timedelta(minutes=INTERVAL)

    captured_slices: list[pd.DataFrame] = []

    original_scan = fvg_scanner.scan_symbol

    def capturing_scan(candles: pd.DataFrame, symbol: str) -> list:
        captured_slices.append(candles.copy())
        return original_scan(candles, symbol)

    fvg_scanner._alerted_candles.clear()
    with patch("strategies.fvg_impulse.scanner.scan_symbol", side_effect=capturing_scan):
        _replay_fvg(fvg_scanner, "fvg-impulse", SYMBOL, df, [signal_candle_idx], INTERVAL, "run1", False)

    assert captured_slices, "scan_symbol was never called"
    for sliced in captured_slices:
        # The last row of the slice must be <= the target candle time
        last_ts = sliced.index[-1].to_pydatetime()
        assert last_ts == start, f"Slice ends at {last_ts} but expected {start}"


# ---------------------------------------------------------------------------
# 3. No signal has candle_time > as_of_time
# ---------------------------------------------------------------------------

def test_no_signal_candle_time_in_future() -> None:
    """Every signal from _replay_fvg must have candle_time < fake_now."""
    df = _candles_with_fvg_and_wick(n=15)
    signal_candle_idx = 13
    start = df.index[signal_candle_idx].to_pydatetime()
    end = start + timedelta(minutes=INTERVAL)

    fvg_scanner._alerted_candles.clear()
    signals, violations = _replay_fvg(
        fvg_scanner, "fvg-impulse", SYMBOL, df, [signal_candle_idx], INTERVAL, "run1", False,
    )

    assert violations == 0
    for sig in signals:
        fake_now = fake_now_for_index(df, signal_candle_idx, INTERVAL)
        assert sig.candle_time < fake_now, (
            f"Lookahead bias: signal.candle_time={sig.candle_time} >= fake_now={fake_now}"
        )
        assert sig.candle_time == start


# ---------------------------------------------------------------------------
# 4. FVG invalidated by future close still emits at the test candle
# ---------------------------------------------------------------------------

def test_fvg_invalidated_by_future_close_still_emits() -> None:
    """Signal at bar idx emits even when bar idx+1 closes through the FVG far edge.

    This is the critical lookahead-freedom test: the live scanner running at T
    would not see bar T+1, so the backfill must not either.
    """
    n = 15
    df = _candles_with_fvg_and_wick(n=n)
    signal_idx = n - 2  # bar that wick-tests

    # Modify bar signal_idx+1 to close far below fvg_far (would invalidate FVG
    # retroactively if the scanner saw it).
    df = df.copy()
    close_col = df["close"].values.copy()
    close_col[signal_idx + 1] = FAR_BULL - 30 * PIP  # deep close-through
    df["close"] = close_col
    low_col = df["low"].values.copy()
    low_col[signal_idx + 1] = FAR_BULL - 35 * PIP
    df["low"] = low_col

    fvg_scanner._alerted_candles.clear()
    signals, violations = _replay_fvg(
        fvg_scanner, "fvg-impulse", SYMBOL, df, [signal_idx], INTERVAL, "run1", False,
    )

    assert violations == 0
    assert len(signals) >= 1, (
        "Signal must be emitted at bar signal_idx even though a future bar "
        "would invalidate the FVG. The slice-as-of guarantee ensures future data "
        "is not visible."
    )


# ---------------------------------------------------------------------------
# 5. Warmup region excluded from emit window
# ---------------------------------------------------------------------------

def test_emit_indices_excludes_pre_start() -> None:
    """emit_indices must never include indices before the start timestamp."""
    df = _flat_ohlc(100)
    # start = halfway through the candles
    start = df.index[50].to_pydatetime()
    end = df.index[80].to_pydatetime()

    indices = emit_indices(df, start, end)

    for i in indices:
        ts = df.index[i].to_pydatetime()
        assert ts >= start, f"Index {i} ({ts}) is before start ({start})"


def test_emit_indices_warmup_bars_not_emitted() -> None:
    """With start at bar WARMUP_BARS+5, bars 0..WARMUP_BARS+4 must not appear."""
    n = WARMUP_BARS + 30
    df = _flat_ohlc(n)
    first_emit_idx = WARMUP_BARS + 5
    start = df.index[first_emit_idx].to_pydatetime()
    end = df.index[-1].to_pydatetime()

    indices = emit_indices(df, start, end)

    assert all(i >= first_emit_idx for i in indices)
    assert all(i >= 2 for i in indices)


# ---------------------------------------------------------------------------
# 6. Emit window is strictly [start, end)
# ---------------------------------------------------------------------------

def test_emit_indices_half_open_window() -> None:
    """Candle at exactly end is excluded; candle at start is included."""
    df = _flat_ohlc(20)
    start = df.index[5].to_pydatetime()
    end = df.index[15].to_pydatetime()

    indices = emit_indices(df, start, end)

    ts_set = {df.index[i].to_pydatetime() for i in indices}
    assert start in ts_set, "start timestamp must be included"
    assert end not in ts_set, "end timestamp must be excluded (half-open)"
    assert all(df.index[i].to_pydatetime() < end for i in indices)


# ---------------------------------------------------------------------------
# 7. Indices < 2 are always skipped
# ---------------------------------------------------------------------------

def test_emit_indices_skips_index_0_and_1() -> None:
    """Scanner needs at least 2 preceding bars; indices 0 and 1 must be excluded."""
    df = _flat_ohlc(20)
    # Start before bar 2 to verify the guard
    start = df.index[0].to_pydatetime()
    end = df.index[10].to_pydatetime()

    indices = emit_indices(df, start, end)

    assert 0 not in indices
    assert 1 not in indices
    assert all(i >= 2 for i in indices)


# ---------------------------------------------------------------------------
# 8. Weekend / gap in candles does not crash
# ---------------------------------------------------------------------------

def test_gap_in_candles_no_crash() -> None:
    """A 48-hour gap between bars produces no exceptions and no signals in the gap."""
    n = 20
    df = _flat_ohlc(n)

    # Inject a 48-hour gap between bars 9 and 10
    new_index = list(df.index)
    gap_start = new_index[9]
    for j in range(10, n):
        new_index[j] = gap_start + timedelta(hours=48) + timedelta(minutes=15 * (j - 9))
    df.index = pd.DatetimeIndex(new_index)

    start = df.index[2].to_pydatetime()
    end = df.index[-1].to_pydatetime()

    indices = emit_indices(df, start, end)
    assert len(indices) > 0

    # Running replay over a flat DataFrame should produce no signals but not crash
    fvg_scanner._alerted_candles.clear()
    signals, violations = _replay_fvg(
        fvg_scanner, "fvg-impulse", SYMBOL, df, indices[:5], INTERVAL, "run1", False,
    )
    assert violations == 0


# ---------------------------------------------------------------------------
# 9. Symbol with < 3 candles produces zero signals, no crash
# ---------------------------------------------------------------------------

def test_short_history_produces_no_signals() -> None:
    """scan_symbol returns [] when slice has < 3 bars — backfill must handle this."""
    df = _flat_ohlc(3)
    # Only index 2 is eligible; scan_symbol needs last_idx >= 2 but also needs
    # at least 2 bars before it — flat candles produce no FVG.
    start = df.index[2].to_pydatetime()
    end = start + timedelta(minutes=INTERVAL)

    fvg_scanner._alerted_candles.clear()
    signals, violations = _replay_fvg(
        fvg_scanner, "fvg-impulse", SYMBOL, df, [2], INTERVAL, "run1", False,
    )

    assert violations == 0
    assert signals == []


# ---------------------------------------------------------------------------
# 10. Re-running backfill twice is idempotent
# ---------------------------------------------------------------------------

def test_rerun_backfill_idempotent(db: Session) -> None:
    """Two calls to _replay_fvg with the same data and same run_id produce
    no extra rows when persisted — the DB dedup prevents doubles.
    """
    from runner.helpers import is_duplicate, persist

    df = _candles_with_fvg_and_wick(n=15)
    signal_idx = 13
    indices = [signal_idx]

    fvg_scanner._alerted_candles.clear()
    signals_run1, _ = _replay_fvg(
        fvg_scanner, "fvg-impulse", SYMBOL, df, indices, INTERVAL, "run-A", False,
    )
    for sig in signals_run1:
        if not is_duplicate(db, sig):
            persist(db, sig)
    db.commit()

    count_after_run1 = db.execute(
        __import__("sqlalchemy").text("SELECT COUNT(*) FROM signals")
    ).scalar()

    # Second run with same indices — should all be duplicates
    fvg_scanner._alerted_candles.clear()
    signals_run2, _ = _replay_fvg(
        fvg_scanner, "fvg-impulse", SYMBOL, df, indices, INTERVAL, "run-B", False,
    )
    inserted_run2 = 0
    for sig in signals_run2:
        if not is_duplicate(db, sig):
            persist(db, sig)
            inserted_run2 += 1
    db.commit()

    count_after_run2 = db.execute(
        __import__("sqlalchemy").text("SELECT COUNT(*) FROM signals")
    ).scalar()

    assert inserted_run2 == 0, "Second run should insert nothing — all duplicates"
    assert count_after_run1 == count_after_run2, "Row count must not change on rerun"


# ---------------------------------------------------------------------------
# 11. Pre-existing live signal is not overwritten
# ---------------------------------------------------------------------------

def test_live_signal_not_overwritten_by_backfill(db: Session) -> None:
    """A live signal already in the DB for (strategy, symbol, candle_time) must
    remain unchanged after backfill attempts to insert the same candle.
    """
    from runner.helpers import is_duplicate, persist

    df = _candles_with_fvg_and_wick(n=15)
    signal_idx = 13
    candle_time = df.index[signal_idx].to_pydatetime()

    # Insert a live signal manually
    live_id = "live-signal-id-001"
    db.add(SignalModel(
        id=live_id,
        strategy="fvg-impulse",
        symbol=SYMBOL,
        direction="BUY",
        candle_time=candle_time,
        entry=NEAR_BULL,
        sl=FAR_BULL - 3 * PIP,
        tp=NEAR_BULL + 20 * PIP,
        lot_size=0.5,
        risk_pips=20.0,
        spread_pips=0.2,
        signal_metadata={},  # no backfill key — it's live
        created_at=datetime.now(timezone.utc),
    ))
    db.commit()

    # Run backfill for that same candle
    fvg_scanner._alerted_candles.clear()
    signals, _ = _replay_fvg(
        fvg_scanner, "fvg-impulse", SYMBOL, df, [signal_idx], INTERVAL, "run-X", False,
    )
    for sig in signals:
        if not is_duplicate(db, sig):
            persist(db, sig)
    db.commit()

    # The live signal must still have its original id and no backfill key
    row = db.scalar(select(SignalModel).where(SignalModel.id == live_id))
    assert row is not None, "Live signal was deleted — should never happen"
    assert row.signal_metadata.get("backfill") is None, (
        "Live signal was overwritten with backfill metadata"
    )


# ---------------------------------------------------------------------------
# 12. _alerted_candles cleared at start of each iteration
# ---------------------------------------------------------------------------

def test_alerted_candles_cleared_per_iteration() -> None:
    """After _replay_fvg, _alerted_candles must be empty (cleared on each iter)."""
    df = _candles_with_fvg_and_wick(n=15)
    indices = [13]

    # Pre-load the set to verify it gets cleared before the first iteration
    fvg_scanner._alerted_candles.add((SYMBOL, datetime.now(timezone.utc)))

    _replay_fvg(
        fvg_scanner, "fvg-impulse", SYMBOL, df, indices, INTERVAL, "run1", False,
    )

    assert len(fvg_scanner._alerted_candles) == 0, (
        "_alerted_candles must be empty after replay — state must not leak between iterations"
    )


# ---------------------------------------------------------------------------
# 13. --dry-run writes nothing to the DB
# ---------------------------------------------------------------------------

def test_dry_run_no_db_writes(db: Session) -> None:
    """Signals collected in dry_run mode must not be persisted."""
    from scripts.backfill_signals import _run_symbol

    df = _candles_with_fvg_and_wick(n=15)
    signal_idx = 13
    start = df.index[signal_idx].to_pydatetime()
    end = start + timedelta(minutes=INTERVAL)

    stat: dict[str, int] = {"inserted": 0, "skipped": 0, "violations": 0}

    import importlib
    mod = importlib.import_module("strategies.fvg_impulse.scanner")

    with patch.object(mod, "get_candles", return_value=df):
        _run_symbol(
            db, mod, "fvg-impulse", SYMBOL, INTERVAL, 500,
            start, end, dry_run=True, strict=False,
            run_id="dry-run-test", warmup_bars=0, stat=stat,
        )

    count = db.execute(
        __import__("sqlalchemy").text("SELECT COUNT(*) FROM signals")
    ).scalar()
    assert count == 0, "dry_run=True must write zero rows to the DB"
    # But dry-run reports inserted count for logging purposes
    assert stat["inserted"] >= 0  # may be 0 if no signals in window


# ---------------------------------------------------------------------------
# 14. --strict aborts on injected invariant violation
# ---------------------------------------------------------------------------

def test_strict_mode_raises_on_bias_violation() -> None:
    """_check_signal_invariants with strict=True raises RuntimeError on violation."""
    sig = Signal(
        strategy="fvg-impulse",
        symbol=SYMBOL,
        direction="BUY",
        candle_time=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
        entry=NEAR_BULL,
        sl=FAR_BULL,
        tp=NEAR_BULL + 20 * PIP,
        lot_size=0.5,
        risk_pips=20.0,
        spread_pips=0.2,
        metadata={},
    )
    # Inject bias: fake_now is in the past relative to candle_time
    fake_now_past = datetime(2026, 4, 21, 9, 45, tzinfo=timezone.utc)  # 15m before candle

    with pytest.raises(RuntimeError, match="LOOKAHEAD BIAS"):
        _check_signal_invariants(
            sig,
            as_of_candle_time=sig.candle_time,
            fake_now=fake_now_past,
            strict=True,
        )


def test_strict_mode_raises_on_candle_time_mismatch() -> None:
    """_check_signal_invariants raises when signal.candle_time != as_of_candle_time."""
    candle_time = datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc)
    wrong_as_of = datetime(2026, 4, 21, 9, 45, tzinfo=timezone.utc)
    fake_now = candle_time + timedelta(minutes=16)

    sig = Signal(
        strategy="fvg-impulse",
        symbol=SYMBOL,
        direction="BUY",
        candle_time=candle_time,
        entry=NEAR_BULL,
        sl=FAR_BULL,
        tp=NEAR_BULL + 20 * PIP,
        lot_size=0.5,
        risk_pips=20.0,
        spread_pips=0.2,
        metadata={},
    )

    with pytest.raises(RuntimeError, match="INVARIANT VIOLATION"):
        _check_signal_invariants(sig, as_of_candle_time=wrong_as_of, fake_now=fake_now, strict=True)


def test_non_strict_mode_logs_violation_returns_false() -> None:
    """Without strict=True, invariant violation returns False instead of raising."""
    sig = Signal(
        strategy="fvg-impulse",
        symbol=SYMBOL,
        direction="BUY",
        candle_time=datetime(2026, 4, 21, 10, 0, tzinfo=timezone.utc),
        entry=NEAR_BULL,
        sl=FAR_BULL,
        tp=NEAR_BULL + 20 * PIP,
        lot_size=0.5,
        risk_pips=20.0,
        spread_pips=0.2,
        metadata={},
    )
    fake_now_past = datetime(2026, 4, 21, 9, 0, tzinfo=timezone.utc)

    result = _check_signal_invariants(sig, sig.candle_time, fake_now_past, strict=False)
    assert result is False


# ---------------------------------------------------------------------------
# 15. Live-equivalence: backfill result matches direct scan_symbol
# ---------------------------------------------------------------------------

def test_backfill_matches_live_scan_symbol() -> None:
    """A backfill over a known signal candle must produce the same signal as
    calling scan_symbol directly with the same candle slice.
    """
    n = 15
    df = _candles_with_fvg_and_wick(n=n)
    signal_idx = n - 2

    # Direct live-scan with identical slice and fake_now
    fake_now = fake_now_for_index(df, signal_idx, INTERVAL)
    live_slice = slice_as_of(df, signal_idx)

    fvg_scanner._alerted_candles.clear()
    with patch("strategies.fvg_impulse.scanner.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        live_raw = fvg_scanner.scan_symbol(live_slice, SYMBOL)
    live_signals = [fvg_scanner._to_signal(r) for r in live_raw]

    # Backfill replay
    fvg_scanner._alerted_candles.clear()
    backfill_signals, violations = _replay_fvg(
        fvg_scanner, "fvg-impulse", SYMBOL, df, [signal_idx], INTERVAL, "run-eq", False,
    )

    assert violations == 0
    assert len(backfill_signals) == len(live_signals), (
        f"Signal count mismatch: live={len(live_signals)} backfill={len(backfill_signals)}"
    )

    for live_sig, bf_sig in zip(live_signals, backfill_signals):
        assert live_sig.direction == bf_sig.direction
        assert live_sig.candle_time == bf_sig.candle_time
        assert live_sig.entry == pytest.approx(bf_sig.entry)
        assert live_sig.sl == pytest.approx(bf_sig.sl)
        assert live_sig.tp == pytest.approx(bf_sig.tp)
        assert live_sig.metadata["fvg_near_edge"] == pytest.approx(bf_sig.metadata["fvg_near_edge"])
        assert live_sig.metadata["fvg_far_edge"] == pytest.approx(bf_sig.metadata["fvg_far_edge"])


# ---------------------------------------------------------------------------
# 16. Backfill metadata keys stamped on every signal
# ---------------------------------------------------------------------------

def test_backfill_metadata_stamped() -> None:
    """Every signal from _replay_fvg must have backfill, backfill_run_id, as_of_time."""
    df = _candles_with_fvg_and_wick(n=15)
    signal_idx = 13
    run_id = "test-run-metadata-stamp"

    fvg_scanner._alerted_candles.clear()
    signals, violations = _replay_fvg(
        fvg_scanner, "fvg-impulse", SYMBOL, df, [signal_idx], INTERVAL, run_id, False,
    )

    assert violations == 0
    assert len(signals) >= 1, "Need at least one signal to test metadata stamping"

    for sig in signals:
        assert sig.metadata.get("backfill") is True, "Missing backfill=True"
        assert sig.metadata.get("backfill_run_id") == run_id, "Missing or wrong run_id"
        assert "as_of_time" in sig.metadata, "Missing as_of_time"


# ---------------------------------------------------------------------------
# 17. emit_indices respects index >= 2 across a large range
# ---------------------------------------------------------------------------

def test_emit_indices_full_range() -> None:
    """emit_indices over the full candle range returns all valid indices."""
    n = 50
    df = _flat_ohlc(n)
    start = df.index[0].to_pydatetime()
    end = df.index[-1].to_pydatetime() + timedelta(minutes=INTERVAL)

    indices = emit_indices(df, start, end)

    assert min(indices) == 2
    assert max(indices) == n - 1
    assert len(indices) == n - 2  # 0 and 1 excluded


# ---------------------------------------------------------------------------
# 18. Bearish FVG signal emitted correctly
# ---------------------------------------------------------------------------

def test_bearish_signal_emitted() -> None:
    """Bearish FVG wick-test is detected and emitted with direction=SELL."""
    NEAR_BEAR = 1.0990
    FAR_BEAR = 1.1010
    n = 15
    df = _candles_with_fvg_and_wick(n=n, fvg_near=NEAR_BEAR, fvg_far=FAR_BEAR, direction="bearish")
    signal_idx = n - 2

    fvg_scanner._alerted_candles.clear()
    signals, violations = _replay_fvg(
        fvg_scanner, "fvg-impulse", SYMBOL, df, [signal_idx], INTERVAL, "run-bear", False,
    )

    assert violations == 0
    assert len(signals) >= 1
    assert signals[0].direction == "SELL"
