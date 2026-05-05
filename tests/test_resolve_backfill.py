"""
tests/test_resolve_backfill.py
------------------------------
Tests for scripts/resolve_backfill.py.

Covers:
  1. TP hit resolves correctly
  2. SL hit resolves correctly
  3. Tie-break: SL wins when both TP and SL touched on same bar
  4. EXPIRED after MAX_RESOLUTION_CANDLES with no hit
  5. No candle data skips group and increments no_data
  6. dry_run=True does not commit (DB still shows resolution=NULL)
  7. Only backfill signals are targeted (live signals untouched)
  8. Already-resolved signals are skipped
  9. --strategy filter processes only matching strategy
 10. --run-id filter processes only matching backfill_run_id
 11. Idempotent re-run resolves 0 on second pass
 12. Report counts match actual DB state after a mixed run
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from sqlalchemy import StaticPool, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.db import Base
from api.models import SignalModel
from runner.resolution_strategies import MAX_RESOLUTION_CANDLES
from scripts.resolve_backfill import BackfillResolveReport, resolve_backfill

# ---------------------------------------------------------------------------
# DB fixtures
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
# Constants
# ---------------------------------------------------------------------------

PIP = 0.0001
ENTRY = 1.1000
TP_BUY = ENTRY + 30 * PIP
SL_BUY = ENTRY - 20 * PIP
TP_SELL = ENTRY - 30 * PIP
SL_SELL = ENTRY + 20 * PIP
STRATEGY = "fvg-impulse"
NOVA_STRATEGY = "nova-candle"
SYMBOL = "EURUSD"
CANDLE_COUNT = MAX_RESOLUTION_CANDLES + 10


# ---------------------------------------------------------------------------
# Signal fixture
# ---------------------------------------------------------------------------

def _make_signal(
    symbol: str = SYMBOL,
    strategy: str = STRATEGY,
    direction: str = "BUY",
    candle_time: datetime | None = None,
    entry: float = ENTRY,
    sl: float = SL_BUY,
    tp: float = TP_BUY,
    backfill: bool = True,
    run_id: str = "test-run",
    resolution: str | None = None,
) -> SignalModel:
    """Build a SignalModel directly (not via backfill script)."""
    if candle_time is None:
        candle_time = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    meta: dict[str, Any] = {}
    if backfill:
        meta["backfill"] = True
        meta["backfill_run_id"] = run_id
    return SignalModel(
        id=str(uuid.uuid4()),
        strategy=strategy,
        symbol=symbol,
        direction=direction,
        candle_time=candle_time,
        entry=entry,
        sl=sl,
        tp=tp,
        lot_size=0.1,
        risk_pips=20.0,
        spread_pips=0.2,
        signal_metadata=meta,
        created_at=datetime.now(timezone.utc),
        resolution=resolution,
    )


# ---------------------------------------------------------------------------
# Candle fixture helpers
# ---------------------------------------------------------------------------

def _make_candle_index(n: int, start: datetime) -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="15min", tz=timezone.utc)


def _flat_candles(n: int, start: datetime, price: float = ENTRY) -> pd.DataFrame:
    idx = _make_candle_index(n, start)
    return pd.DataFrame({
        "open":  np.full(n, price),
        "high":  np.full(n, price + 5 * PIP),
        "low":   np.full(n, price - 5 * PIP),
        "close": np.full(n, price),
        "volume": np.ones(n),
    }, index=idx)


def _make_candles_tp_hit(start: datetime, signal_idx: int, n: int, direction: str = "BUY") -> pd.DataFrame:
    """Build n bars where TP is reached 2 bars after signal_idx."""
    tp = TP_BUY if direction == "BUY" else TP_SELL
    df = _flat_candles(n, start, ENTRY)
    h, lo = df["high"].values.copy(), df["low"].values.copy()
    if direction == "BUY":
        h[signal_idx + 2] = tp + PIP
    else:
        lo[signal_idx + 2] = tp - PIP
    df["high"] = h
    df["low"] = lo
    return df


def _make_candles_sl_hit(start: datetime, signal_idx: int, n: int, direction: str = "BUY") -> pd.DataFrame:
    """Build n bars where SL is reached 2 bars after signal_idx."""
    sl = SL_BUY if direction == "BUY" else SL_SELL
    df = _flat_candles(n, start, ENTRY)
    h, lo = df["high"].values.copy(), df["low"].values.copy()
    if direction == "BUY":
        lo[signal_idx + 2] = sl - PIP
    else:
        h[signal_idx + 2] = sl + PIP
    df["high"] = h
    df["low"] = lo
    return df


def _make_candles_both_hit(start: datetime, signal_idx: int, n: int) -> pd.DataFrame:
    """Build n bars where both TP and SL are touched on the same bar (tie-break: SL wins)."""
    df = _flat_candles(n, start, ENTRY)
    h, lo = df["high"].values.copy(), df["low"].values.copy()
    h[signal_idx + 2] = TP_BUY + PIP
    lo[signal_idx + 2] = SL_BUY - PIP
    df["high"] = h
    df["low"] = lo
    return df


def _make_candles_neither_hit(start: datetime) -> pd.DataFrame:
    """Build MAX_RESOLUTION_CANDLES+5 flat bars that never reach TP or SL."""
    n = MAX_RESOLUTION_CANDLES + 5
    return _flat_candles(n, start, ENTRY)


# ---------------------------------------------------------------------------
# Helpers to insert signals and run resolve_backfill against a mocked DB
# ---------------------------------------------------------------------------

def _run_resolve(
    db: Session,
    df: pd.DataFrame | None,
    signals: list[SignalModel],
    strategy: str = STRATEGY,
    dry_run: bool = False,
    strict: bool = False,
    filter_strategy: list[str] | None = None,
    run_id_filter: str | None = None,
) -> BackfillResolveReport:
    """Insert signals, patch get_candles + SessionLocal, run resolve_backfill."""
    for sig in signals:
        db.add(sig)
    db.commit()

    # resolve_backfill owns and closes its session via finally: db.close().
    # Patch close() to a no-op so the test session stays open for assertions.
    with (
        patch("scripts.resolve_backfill.get_candles", return_value=df),
        patch("scripts.resolve_backfill.SessionLocal", return_value=db),
        patch.object(db, "close"),
    ):
        report = resolve_backfill(
            dry_run=dry_run,
            strict=strict,
            strategies=filter_strategy,
            run_id=run_id_filter,
        )
    return report


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_tp_hit_resolves_correctly(db: Session) -> None:
    """BUY signal with TP within window → resolution='TP_HIT', resolved_price=signal.tp."""
    ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    sig = _make_signal(direction="BUY", candle_time=ct)
    df = _make_candles_tp_hit(ct, signal_idx=0, n=CANDLE_COUNT, direction="BUY")

    _run_resolve(db, df, [sig])

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert row.resolution == "TP_HIT"
    assert row.resolved_price == pytest.approx(TP_BUY)


def test_sl_hit_resolves_correctly(db: Session) -> None:
    """SELL signal with SL hit → resolution='SL_HIT'."""
    ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    sig = _make_signal(direction="SELL", candle_time=ct, sl=SL_SELL, tp=TP_SELL)
    df = _make_candles_sl_hit(ct, signal_idx=0, n=CANDLE_COUNT, direction="SELL")

    _run_resolve(db, df, [sig])

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert row.resolution == "SL_HIT"
    assert row.resolved_price == pytest.approx(SL_SELL)


def test_tie_break_sl_wins(db: Session) -> None:
    """Candle touching both SL and TP → resolution='SL_HIT' (conservative tie-break)."""
    ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    sig = _make_signal(direction="BUY", candle_time=ct)
    df = _make_candles_both_hit(ct, signal_idx=0, n=CANDLE_COUNT)

    _run_resolve(db, df, [sig])

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert row.resolution == "SL_HIT"


def test_expired_after_max_candles(db: Session) -> None:
    """Neither TP nor SL hit within MAX_RESOLUTION_CANDLES → resolution='EXPIRED'."""
    ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    sig = _make_signal(direction="BUY", candle_time=ct)
    df = _make_candles_neither_hit(ct)

    _run_resolve(db, df, [sig])

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert row.resolution == "EXPIRED"


def test_no_candle_data_skips_group(db: Session) -> None:
    """get_candles returns None → signal stays unresolved, no_data incremented."""
    ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    sig = _make_signal(direction="BUY", candle_time=ct)

    report = _run_resolve(db, df=None, signals=[sig])

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert row.resolution is None
    assert report.no_data == 1


def test_dry_run_does_not_commit(db: Session) -> None:
    """dry_run=True → DB still shows resolution=NULL after run."""
    ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    sig = _make_signal(direction="BUY", candle_time=ct)
    df = _make_candles_tp_hit(ct, signal_idx=0, n=CANDLE_COUNT)

    report = _run_resolve(db, df, [sig], dry_run=True)

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert row.resolution is None
    assert report.dry_run is True


def test_only_backfill_signals_targeted(db: Session) -> None:
    """Live signal (no backfill key) stays unresolved; backfill signal is resolved."""
    ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    live_sig = _make_signal(direction="BUY", candle_time=ct, backfill=False)
    bf_sig = _make_signal(direction="BUY", candle_time=ct + timedelta(hours=1))
    df = _make_candles_tp_hit(ct, signal_idx=0, n=CANDLE_COUNT)

    _run_resolve(db, df, [live_sig, bf_sig])

    live_row = db.scalar(select(SignalModel).where(SignalModel.id == live_sig.id))
    bf_row = db.scalar(select(SignalModel).where(SignalModel.id == bf_sig.id))
    assert live_row.resolution is None
    assert bf_row.resolution is not None


def test_already_resolved_signals_skipped(db: Session) -> None:
    """Signal with existing resolution is not re-processed."""
    ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    sig = _make_signal(direction="BUY", candle_time=ct, resolution="TP_HIT")
    df = _make_candles_sl_hit(ct, signal_idx=0, n=CANDLE_COUNT)

    _run_resolve(db, df, [sig])

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert row.resolution == "TP_HIT"


def test_strategy_filter(db: Session) -> None:
    """--strategy fvg-impulse → only fvg-impulse signals processed; nova-candle left unresolved."""
    ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    fvg_sig = _make_signal(strategy=STRATEGY, direction="BUY", candle_time=ct)
    nova_sig = _make_signal(strategy=NOVA_STRATEGY, direction="BUY", candle_time=ct + timedelta(hours=1))
    df = _make_candles_tp_hit(ct, signal_idx=0, n=CANDLE_COUNT)

    _run_resolve(db, df, [fvg_sig, nova_sig], filter_strategy=[STRATEGY])

    fvg_row = db.scalar(select(SignalModel).where(SignalModel.id == fvg_sig.id))
    nova_row = db.scalar(select(SignalModel).where(SignalModel.id == nova_sig.id))
    assert fvg_row.resolution is not None
    assert nova_row.resolution is None


def test_run_id_filter(db: Session) -> None:
    """--run-id filter → only matching backfill_run_id signals processed."""
    ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    target_sig = _make_signal(direction="BUY", candle_time=ct, run_id="prod-run-001")
    other_sig = _make_signal(direction="BUY", candle_time=ct + timedelta(hours=1), run_id="prod-run-002")
    df = _make_candles_tp_hit(ct, signal_idx=0, n=CANDLE_COUNT)

    _run_resolve(db, df, [target_sig, other_sig], run_id_filter="prod-run-001")

    target_row = db.scalar(select(SignalModel).where(SignalModel.id == target_sig.id))
    other_row = db.scalar(select(SignalModel).where(SignalModel.id == other_sig.id))
    assert target_row.resolution is not None
    assert other_row.resolution is None


def test_idempotent_rerun(db: Session) -> None:
    """Second run on same signals resolves 0 (already resolved)."""
    ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    sig = _make_signal(direction="BUY", candle_time=ct)
    df = _make_candles_tp_hit(ct, signal_idx=0, n=CANDLE_COUNT)

    _run_resolve(db, df, [sig])
    report2 = _run_resolve(db, df, [], dry_run=False)

    assert report2.resolved == 0


def test_report_counts_accurate(db: Session) -> None:
    """report.resolved matches actual resolved DB rows after a mixed TP/SL/expired run."""
    base_ct = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
    tp_sig = _make_signal(direction="BUY", candle_time=base_ct)
    sl_sig = _make_signal(direction="BUY", candle_time=base_ct + timedelta(hours=1))
    expired_sig = _make_signal(direction="BUY", candle_time=base_ct + timedelta(hours=2))

    tp_df = _make_candles_tp_hit(base_ct, signal_idx=0, n=CANDLE_COUNT)
    sl_df = _make_candles_sl_hit(base_ct + timedelta(hours=1), signal_idx=0, n=CANDLE_COUNT)
    expired_df = _make_candles_neither_hit(base_ct + timedelta(hours=2))

    for sig in [tp_sig, sl_sig, expired_sig]:
        db.add(sig)
    db.commit()

    dfs = [tp_df, sl_df, expired_df]
    df_iter = iter(dfs)

    with (
        patch("scripts.resolve_backfill.get_candles", side_effect=lambda *a, **kw: next(df_iter)),
        patch("scripts.resolve_backfill.SessionLocal", return_value=db),
    ):
        report = resolve_backfill()

    resolved_in_db = db.scalar(
        __import__("sqlalchemy").text("SELECT COUNT(*) FROM signals WHERE resolution IS NOT NULL")
    )
    assert report.resolved == resolved_in_db
    assert report.resolved == 3
