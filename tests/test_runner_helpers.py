"""
tests/test_runner_helpers.py
-----------------------------
Unit tests for runner/helpers.py:
  - is_market_open
  - is_duplicate
  - persist
  - wait_for_next_candle (timing calculation only — no sleep)
  - discover_strategies
"""
from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from api.models import SignalModel
from runner.helpers import (
    SCAN_INTERVAL_SECONDS,
    discover_strategies,
    is_duplicate,
    is_market_open,
    persist,
    wait_for_next_candle,
)
from shared.signal import Signal

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CANDLE_TIME = datetime(2025, 1, 15, 12, 0, tzinfo=timezone.utc)
_MONDAY_TRADING = datetime(2025, 1, 13, 10, 0, tzinfo=timezone.utc)   # Mon 10:00 UTC
_FRIDAY_CLOSED = datetime(2025, 1, 17, 22, 30, tzinfo=timezone.utc)   # Fri 22:30 UTC
_SATURDAY = datetime(2025, 1, 18, 12, 0, tzinfo=timezone.utc)         # Sat
_SUNDAY_EARLY = datetime(2025, 1, 19, 10, 0, tzinfo=timezone.utc)     # Sun before 22:00
_SUNDAY_OPEN = datetime(2025, 1, 19, 22, 0, tzinfo=timezone.utc)      # Sun exactly 22:00

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    *,
    strategy: str = "fvg-impulse",
    symbol: str = "EURUSD",
    candle_time: datetime = _CANDLE_TIME,
) -> Signal:
    """Return a minimal Signal with the given identity fields."""
    return Signal(
        strategy=strategy,
        symbol=symbol,
        direction="BUY",
        candle_time=candle_time,
        entry=1.08500,
        sl=1.08200,
        tp=1.09100,
        lot_size=0.50,
        risk_pips=30.0,
        spread_pips=1.2,
        metadata={},
    )


def _insert_signal_model(db: Session, sig: Signal) -> SignalModel:
    """Insert a SignalModel row matching the given Signal and commit."""
    model = SignalModel(
        id=sig.id,
        strategy=sig.strategy,
        symbol=sig.symbol,
        direction=sig.direction,
        candle_time=sig.candle_time,
        entry=sig.entry,
        sl=sig.sl,
        tp=sig.tp,
        lot_size=sig.lot_size,
        risk_pips=sig.risk_pips,
        spread_pips=sig.spread_pips,
        signal_metadata=sig.metadata,
        created_at=sig.created_at,
    )
    db.add(model)
    db.commit()
    return model


# ---------------------------------------------------------------------------
# is_market_open
# ---------------------------------------------------------------------------


def test_market_open_monday_returns_true() -> None:
    """Standard weekday trading hour must return True."""
    with patch("runner.helpers.datetime") as mock_dt:
        mock_dt.now.return_value = _MONDAY_TRADING
        assert is_market_open() is True


def test_market_closed_friday_after_22() -> None:
    """Friday at or after 22:00 UTC must return False."""
    with patch("runner.helpers.datetime") as mock_dt:
        mock_dt.now.return_value = _FRIDAY_CLOSED
        assert is_market_open() is False


def test_market_closed_saturday() -> None:
    """Saturday is always closed."""
    with patch("runner.helpers.datetime") as mock_dt:
        mock_dt.now.return_value = _SATURDAY
        assert is_market_open() is False


def test_market_closed_sunday_before_22() -> None:
    """Sunday before 22:00 UTC is closed."""
    with patch("runner.helpers.datetime") as mock_dt:
        mock_dt.now.return_value = _SUNDAY_EARLY
        assert is_market_open() is False


def test_market_open_sunday_at_22() -> None:
    """Sunday at exactly 22:00 UTC is the market open boundary — must return True."""
    with patch("runner.helpers.datetime") as mock_dt:
        mock_dt.now.return_value = _SUNDAY_OPEN
        assert is_market_open() is True


# ---------------------------------------------------------------------------
# is_duplicate
# ---------------------------------------------------------------------------


def test_is_duplicate_returns_false_when_no_match(db: Session) -> None:
    """No existing row → is_duplicate must return False."""
    sig = _make_signal()
    assert is_duplicate(db, sig) is False


def test_is_duplicate_returns_true_when_row_exists(db: Session) -> None:
    """After inserting the same (strategy, symbol, candle_time), must return True."""
    sig = _make_signal()
    _insert_signal_model(db, sig)
    # Build a new Signal with same identity but a different id
    duplicate = _make_signal()
    assert is_duplicate(db, duplicate) is True


def test_is_duplicate_different_symbol_returns_false(db: Session) -> None:
    """Same strategy + candle_time but different symbol must not be flagged."""
    sig = _make_signal(symbol="EURUSD")
    _insert_signal_model(db, sig)
    other = _make_signal(symbol="GBPUSD")
    assert is_duplicate(db, other) is False


def test_is_duplicate_different_candle_time_returns_false(db: Session) -> None:
    """Same strategy + symbol but a later candle_time must not be flagged."""
    sig = _make_signal(candle_time=_CANDLE_TIME)
    _insert_signal_model(db, sig)
    later = _make_signal(candle_time=_CANDLE_TIME + timedelta(minutes=15))
    assert is_duplicate(db, later) is False


# ---------------------------------------------------------------------------
# persist
# ---------------------------------------------------------------------------


def test_persist_inserts_new_signal(db: Session) -> None:
    """persist() on a fresh Signal must return True and write to the DB."""
    sig = _make_signal()
    result = persist(db, sig)
    assert result is True
    row = db.get(SignalModel, sig.id)
    assert row is not None
    assert row.strategy == sig.strategy
    assert row.symbol == sig.symbol


def test_persist_returns_false_on_duplicate(db: Session) -> None:
    """persist() on a duplicate (IntegrityError) must return False without raising."""
    sig = _make_signal()
    _insert_signal_model(db, sig)
    # Attempt to persist a signal with the same unique key
    duplicate = _make_signal()
    duplicate.id = str(uuid.uuid4())  # different PK so we hit the unique constraint, not PK dupe
    result = persist(db, duplicate)
    assert result is False


def test_persist_session_usable_after_integrity_error(db: Session) -> None:
    """The session must still be functional after a failed persist()."""
    sig = _make_signal()
    _insert_signal_model(db, sig)

    duplicate = _make_signal()
    duplicate.id = str(uuid.uuid4())
    persist(db, duplicate)  # triggers IntegrityError internally

    # Session must still accept new valid inserts
    new_sig = _make_signal(symbol="GBPUSD")
    result = persist(db, new_sig)
    assert result is True
    assert db.get(SignalModel, new_sig.id) is not None


def test_persist_stores_metadata(db: Session) -> None:
    """signal_metadata dict must be persisted and retrievable."""
    sig = _make_signal()
    sig.metadata = {"fvg_size": 12, "atr": 0.0025}
    persist(db, sig)
    row = db.get(SignalModel, sig.id)
    assert row is not None
    assert row.signal_metadata == {"fvg_size": 12, "atr": 0.0025}


# ---------------------------------------------------------------------------
# wait_for_next_candle — timing calculation
#
# wait_for_next_candle() calls time.sleep() internally. We patch sleep to a
# no-op and capture the seconds that would have been slept via a side-effect
# list so we can assert on the computed wait without blocking.
# ---------------------------------------------------------------------------

_BUFFER: int = 5  # hardcoded buffer in helpers.py


def _capture_sleep_seconds(fake_now: datetime) -> int:
    """Run wait_for_next_candle with frozen time; return seconds passed to sleep."""
    captured: list[float] = []

    with patch("runner.helpers.datetime") as mock_dt, \
         patch("runner.helpers.time.sleep", side_effect=captured.append):
        mock_dt.now.return_value = fake_now
        mock_dt.fromtimestamp.side_effect = datetime.fromtimestamp
        wait_for_next_candle()

    assert len(captured) == 1, "time.sleep should be called exactly once"
    return int(captured[0])


def test_wait_for_next_candle_returns_positive_seconds() -> None:
    """Any time input must produce a positive wait duration."""
    fake_now = datetime(2025, 1, 13, 10, 7, 30, tzinfo=timezone.utc)
    seconds = _capture_sleep_seconds(fake_now)
    assert seconds > 0


def test_wait_for_next_candle_just_after_boundary() -> None:
    """30 seconds past a 5-minute boundary → wait ≈ SCAN_INTERVAL + buffer - 30."""
    fake_now = datetime(2025, 1, 13, 10, 0, 30, tzinfo=timezone.utc)
    seconds = _capture_sleep_seconds(fake_now)
    expected = SCAN_INTERVAL_SECONDS - 30 + _BUFFER
    assert abs(seconds - expected) <= 1


def test_wait_for_next_candle_just_before_boundary() -> None:
    """10 seconds before a 5-minute boundary → wait ≈ SCAN_INTERVAL + buffer - (interval-10)."""
    interval_minutes = max(1, SCAN_INTERVAL_SECONDS // 60)
    # Place now at (interval - 10) seconds past the last boundary
    elapsed = SCAN_INTERVAL_SECONDS - 10
    minute_offset = elapsed // 60
    second_offset = elapsed % 60
    fake_now = datetime(2025, 1, 13, 10, minute_offset, second_offset, tzinfo=timezone.utc)
    seconds = _capture_sleep_seconds(fake_now)
    # seconds_to_wait = SCAN_INTERVAL - elapsed + buffer = 10 + 5 = 15
    # But if <= buffer, an extra interval is added; 15 > 5, so no extra interval
    expected = 10 + _BUFFER
    assert abs(seconds - expected) <= 1


def test_wait_for_next_candle_at_exact_boundary_adds_extra_interval() -> None:
    """At a boundary second=0, min=0: elapsed=0, wait = interval+buffer.
    Since that equals exactly interval+buffer and buffer >= buffer the guard
    seconds_to_wait <= 5 is not triggered; result is interval + buffer.
    """
    fake_now = datetime(2025, 1, 13, 10, 0, 0, tzinfo=timezone.utc)
    seconds = _capture_sleep_seconds(fake_now)
    # elapsed=0 → seconds_to_wait = SCAN_INTERVAL + buffer = 305 (default)
    expected = SCAN_INTERVAL_SECONDS + _BUFFER
    assert abs(seconds - expected) <= 1


# ---------------------------------------------------------------------------
# discover_strategies
# ---------------------------------------------------------------------------


def test_discover_strategies_returns_non_empty_dict() -> None:
    """At least one strategy must be discovered from the real strategies/ directory."""
    strategies = discover_strategies()
    assert len(strategies) > 0


def test_discover_strategies_values_are_callable() -> None:
    """Every value in the returned dict must be callable (the scan function)."""
    strategies = discover_strategies()
    for slug, scan_fn in strategies.items():
        assert callable(scan_fn), f"scan for '{slug}' is not callable"


def test_discover_strategies_keys_are_kebab_case() -> None:
    """Strategy slugs must use hyphens not underscores (folder name is normalised)."""
    strategies = discover_strategies()
    for slug in strategies:
        assert "_" not in slug, f"slug '{slug}' still contains underscores"


def test_discover_strategies_includes_fvg_impulse() -> None:
    """The fvg-impulse strategy is present in the repository and must be found."""
    strategies = discover_strategies()
    assert "fvg-impulse" in strategies
