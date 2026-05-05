"""
tests/test_enrich_backfill.py
------------------------------
Tests for scripts/enrich_backfill.py.

Covers:
  1. Signal missing params gets them written
  2. Signal already has params is skipped
  3. Idempotent — second run skips all
  4. Dry-run does not commit
  5. Partial params (some None) still written
  6. No candle data — enrich_with_candles returns [] → no_candle_data incremented
  7. strategy filter — only matching strategy processed
  8. from/to date filter — signal outside range skipped
  9. Report counts accurate after mixed run
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from sqlalchemy import StaticPool, create_engine, select
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api.db import Base
from api.models import SignalModel
from scripts.enrich_backfill import ANALYTICS_PARAMS_KEY, EnrichReport, enrich_backfill

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

STRATEGY = "fvg-impulse"
ALT_STRATEGY = "nova-candle"
SYMBOL = "EURUSD"
BASE_TIME = datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)
GOOD_PARAMS: dict[str, Any] = {"atr": 0.0012, "session": "london"}
PARTIAL_PARAMS: dict[str, Any] = {"atr": 0.0012, "session": None}


# ---------------------------------------------------------------------------
# Signal factory
# ---------------------------------------------------------------------------

def _make_signal(
    strategy: str = STRATEGY,
    symbol: str = SYMBOL,
    resolution: str = "TP_HIT",
    candle_time: datetime = BASE_TIME,
    existing_params: dict[str, Any] | None = None,
) -> SignalModel:
    """Build a resolved SignalModel for use in tests."""
    meta: dict[str, Any] = {}
    if existing_params is not None:
        meta[ANALYTICS_PARAMS_KEY] = existing_params
    return SignalModel(
        id=str(uuid.uuid4()),
        strategy=strategy,
        symbol=symbol,
        direction="BUY",
        candle_time=candle_time,
        entry=1.1000,
        sl=1.0980,
        tp=1.1030,
        lot_size=0.1,
        risk_pips=20.0,
        spread_pips=0.2,
        signal_metadata=meta,
        created_at=datetime.now(timezone.utc),
        resolution=resolution,
    )


def _enriched_rows(signals: list[SignalModel], params: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the list[dict] that enrich_with_candles would return."""
    return [{"id": s.id, "params": params} for s in signals]


# ---------------------------------------------------------------------------
# Test runner helper
# ---------------------------------------------------------------------------

def _run(
    db: Session,
    signals: list[SignalModel],
    enriched_return: list[dict[str, Any]],
    *,
    dry_run: bool = False,
    strategy: str | None = None,
    symbol: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = 500,
    enrich_side_effect: Any = None,
) -> EnrichReport:
    """Insert signals, patch dependencies, run enrich_backfill, return report."""
    for sig in signals:
        db.add(sig)
    db.commit()

    enrich_mock = (
        enrich_side_effect
        if enrich_side_effect is not None
        else (lambda _sigs: enriched_return)
    )

    with (
        patch("scripts.enrich_backfill.enrich_with_candles", side_effect=enrich_mock),
        patch("scripts.enrich_backfill.SessionLocal", return_value=db),
        patch.object(db, "close"),
    ):
        return enrich_backfill(
            dry_run=dry_run,
            strategy=strategy,
            symbol=symbol,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
        )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_missing_params_gets_written(db: Session) -> None:
    """Signal without _analytics_params has params written after run."""
    sig = _make_signal()
    report = _run(db, [sig], _enriched_rows([sig], GOOD_PARAMS))

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert row.signal_metadata[ANALYTICS_PARAMS_KEY] == GOOD_PARAMS
    assert report.params_written == 1
    assert report.skipped == 0


def test_existing_params_skipped(db: Session) -> None:
    """Signal already having _analytics_params is excluded by the SQL filter and not overwritten.

    The SQL query's NOT LIKE guard is the primary idempotency gate — signals with
    existing params never reach Python-level processing, so processed and skipped stay 0.
    """
    existing = {"atr": 99.0}
    sig = _make_signal(existing_params=existing)
    report = _run(db, [sig], [])

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert row.signal_metadata[ANALYTICS_PARAMS_KEY] == existing
    assert report.processed == 0
    assert report.params_written == 0


def test_idempotent_second_run(db: Session) -> None:
    """Second run on enriched signals reports processed=0.

    After the first run writes _analytics_params, the SQL filter excludes the
    signal on the next run — the NOT LIKE guard is the idempotency mechanism.
    """
    sig = _make_signal()
    _run(db, [sig], _enriched_rows([sig], GOOD_PARAMS))

    db.expire_all()
    report2 = _run(db, [], [], limit=500)

    assert report2.processed == 0
    assert report2.params_written == 0


def test_dry_run_does_not_commit(db: Session) -> None:
    """dry_run=True → DB still has no _analytics_params after run."""
    sig = _make_signal()
    report = _run(db, [sig], _enriched_rows([sig], GOOD_PARAMS), dry_run=True)

    db.expire_all()
    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert ANALYTICS_PARAMS_KEY not in (row.signal_metadata or {})
    assert report.dry_run is True


def test_partial_params_written_and_counted(db: Session) -> None:
    """Params with some None values are still written; params_partial incremented."""
    sig = _make_signal()
    report = _run(db, [sig], _enriched_rows([sig], PARTIAL_PARAMS))

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert row.signal_metadata[ANALYTICS_PARAMS_KEY] == PARTIAL_PARAMS
    assert report.params_written == 1
    assert report.params_partial == 1


def test_no_candle_data_enrich_returns_empty(db: Session) -> None:
    """enrich_with_candles returning [] → signal stays missing params, no_candle_data incremented."""
    sig = _make_signal()
    report = _run(db, [sig], enriched_return=[], enrich_side_effect=lambda _: [])

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert ANALYTICS_PARAMS_KEY not in (row.signal_metadata or {})
    assert report.no_candle_data == 1
    assert report.params_written == 0


def test_no_candle_data_enrich_raises(db: Session) -> None:
    """enrich_with_candles raising → signal stays missing params, no_candle_data incremented."""
    sig = _make_signal()

    def _raise(_sigs: list[SignalModel]) -> list[dict[str, Any]]:
        raise RuntimeError("candle fetch failed")

    report = _run(db, [sig], enriched_return=[], enrich_side_effect=_raise)

    row = db.scalar(select(SignalModel).where(SignalModel.id == sig.id))
    assert ANALYTICS_PARAMS_KEY not in (row.signal_metadata or {})
    assert report.no_candle_data == 1


def test_strategy_filter(db: Session) -> None:
    """Only the matching strategy is enriched; the other is untouched."""
    target = _make_signal(strategy=STRATEGY)
    other = _make_signal(strategy=ALT_STRATEGY)

    def _enrich(sigs: list[SignalModel]) -> list[dict[str, Any]]:
        return _enriched_rows(sigs, GOOD_PARAMS)

    report = _run(
        db, [target, other], enriched_return=[],
        strategy=STRATEGY,
        enrich_side_effect=_enrich,
    )

    target_row = db.scalar(select(SignalModel).where(SignalModel.id == target.id))
    other_row = db.scalar(select(SignalModel).where(SignalModel.id == other.id))

    assert ANALYTICS_PARAMS_KEY in (target_row.signal_metadata or {})
    assert ANALYTICS_PARAMS_KEY not in (other_row.signal_metadata or {})
    assert report.params_written == 1


def test_from_to_date_filter(db: Session) -> None:
    """Signal outside from/to window is not processed."""
    inside = _make_signal(candle_time=BASE_TIME)
    outside = _make_signal(candle_time=BASE_TIME + timedelta(days=10))

    def _enrich(sigs: list[SignalModel]) -> list[dict[str, Any]]:
        return _enriched_rows(sigs, GOOD_PARAMS)

    to_boundary = BASE_TIME + timedelta(days=5)
    report = _run(
        db, [inside, outside], enriched_return=[],
        from_date=BASE_TIME - timedelta(days=1),
        to_date=to_boundary,
        enrich_side_effect=_enrich,
    )

    inside_row = db.scalar(select(SignalModel).where(SignalModel.id == inside.id))
    outside_row = db.scalar(select(SignalModel).where(SignalModel.id == outside.id))

    assert ANALYTICS_PARAMS_KEY in (inside_row.signal_metadata or {})
    assert ANALYTICS_PARAMS_KEY not in (outside_row.signal_metadata or {})
    assert report.params_written == 1


def test_report_counts_accurate_mixed_run(db: Session) -> None:
    """params_written + no_candle_data equals signals visible to the query.

    already_done is excluded by the SQL NOT LIKE filter before any Python logic
    runs, so it never appears in any report counter.  The two signals that pass
    the SQL filter contribute exactly one params_written and one no_candle_data.
    """
    enrichable = _make_signal(strategy=STRATEGY, symbol=SYMBOL, candle_time=BASE_TIME)
    already_done = _make_signal(
        strategy=STRATEGY,
        symbol="GBPUSD",
        candle_time=BASE_TIME + timedelta(hours=1),
        existing_params={"atr": 1.0},
    )
    no_data = _make_signal(strategy=ALT_STRATEGY, symbol=SYMBOL, candle_time=BASE_TIME + timedelta(hours=2))

    def _enrich(sigs: list[SignalModel]) -> list[dict[str, Any]]:
        if any(s.strategy == ALT_STRATEGY for s in sigs):
            return []
        return _enriched_rows(sigs, GOOD_PARAMS)

    report = _run(
        db, [enrichable, already_done, no_data],
        enriched_return=[],
        enrich_side_effect=_enrich,
    )

    assert report.params_written == 1
    assert report.no_candle_data == 1
    assert report.params_written + report.no_candle_data == 2
