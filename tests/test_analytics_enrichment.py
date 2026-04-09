"""
tests/test_analytics_enrichment.py
-----------------------------------
Integration tests for analytics/enrichment.py: fetch_resolved and enrich_batch.
Uses in-memory SQLite via the db fixture.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from analytics.enrichment import enrich_batch, fetch_resolved
from api.models import SignalModel


def _insert_signal(
    db: Session,
    *,
    strategy: str = "fvg-impulse",
    symbol: str = "EURUSD",
    resolution: str = "TP_HIT",
    candle_hour: int = 10,
    risk_pips: float = 10.0,
    spread_pips: float = 1.0,
    metadata: dict | None = None,
) -> SignalModel:
    """Insert a resolved signal and return it."""
    sig = SignalModel(
        id=str(uuid.uuid4()),
        strategy=strategy,
        symbol=symbol,
        direction="BUY",
        candle_time=datetime(2025, 3, 10, candle_hour, 0, tzinfo=timezone.utc),
        entry=1.08500,
        sl=1.08200,
        tp=1.08800,
        lot_size=0.5,
        risk_pips=risk_pips,
        spread_pips=spread_pips,
        signal_metadata=metadata or {},
        created_at=datetime.now(timezone.utc),
        resolution=resolution,
        resolved_at=datetime.now(timezone.utc),
        resolved_price=1.08800,
        resolution_candles=5,
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig


# ---------------------------------------------------------------------------
# fetch_resolved
# ---------------------------------------------------------------------------


def test_fetch_resolved_returns_tp_and_sl(db: Session) -> None:
    _insert_signal(db, resolution="TP_HIT", candle_hour=10)
    _insert_signal(db, resolution="SL_HIT", candle_hour=11)
    _insert_signal(db, resolution=None, candle_hour=12)  # pending — excluded
    results = fetch_resolved(db)
    assert len(results) == 2


def test_fetch_resolved_filters_strategy(db: Session) -> None:
    _insert_signal(db, strategy="fvg-impulse", candle_hour=10)
    _insert_signal(db, strategy="nova-candle", candle_hour=11)
    results = fetch_resolved(db, strategy="fvg-impulse")
    assert len(results) == 1
    assert results[0].strategy == "fvg-impulse"


def test_fetch_resolved_filters_symbol(db: Session) -> None:
    _insert_signal(db, symbol="EURUSD", candle_hour=10)
    _insert_signal(db, symbol="GBPUSD", candle_hour=11)
    results = fetch_resolved(db, symbol="EURUSD")
    assert len(results) == 1


def test_fetch_resolved_respects_limit(db: Session) -> None:
    for i in range(5):
        _insert_signal(db, candle_hour=i + 1, symbol=f"SYM{i}")
    results = fetch_resolved(db, limit=3)
    assert len(results) == 3


def test_fetch_resolved_clamps_limit(db: Session) -> None:
    results = fetch_resolved(db, limit=5000)
    assert len(results) == 0  # no signals, but didn't crash


def test_fetch_resolved_excludes_expired(db: Session) -> None:
    _insert_signal(db, resolution="EXPIRED")
    assert len(fetch_resolved(db)) == 0


# ---------------------------------------------------------------------------
# enrich_batch
# ---------------------------------------------------------------------------


def test_enrich_batch_adds_params(db: Session) -> None:
    _insert_signal(db, strategy="fvg-impulse", candle_hour=10)
    signals = fetch_resolved(db)
    enriched = enrich_batch(signals)
    assert len(enriched) == 1
    row = enriched[0]
    assert "params" in row
    assert row["params"]["session_label"] == "LONDON"
    assert row["params"]["day_of_week"] == row["candle_time"].weekday()
    assert row["params"]["pair_category"] == "MAJOR"


def test_enrich_batch_preserves_signal_fields(db: Session) -> None:
    _insert_signal(db, strategy="fvg-impulse", symbol="GBPUSD")
    signals = fetch_resolved(db)
    enriched = enrich_batch(signals)
    row = enriched[0]
    assert row["strategy"] == "fvg-impulse"
    assert row["symbol"] == "GBPUSD"
    assert row["resolution"] == "TP_HIT"
    assert "id" in row
    assert "candle_time" in row


def test_enrich_batch_fvg_metadata_params(db: Session) -> None:
    _insert_signal(
        db,
        strategy="fvg-impulse",
        metadata={"fvg_age": 3, "fvg_width_pips": 4.5},
    )
    signals = fetch_resolved(db)
    enriched = enrich_batch(signals)
    params = enriched[0]["params"]
    assert params["fvg_age"] == 3
    assert params["fvg_width_pips"] == 4.5


def test_enrich_batch_empty_list() -> None:
    assert enrich_batch([]) == []
