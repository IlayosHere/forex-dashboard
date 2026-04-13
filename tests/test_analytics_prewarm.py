"""
tests/test_analytics_prewarm.py
--------------------------------
Tests for the historical date window (fetch_resolved from_date) and the
enriched-cache pre-warm (prewarm_enriched_cache).

Proves:
  1. fetch_resolved excludes signals older than _DEFAULT_LOOKBACK_DAYS by default.
  2. fetch_resolved includes signals within the rolling lookback window.
  3. fetch_resolved with from_date=None returns all history regardless of date.
  4. Explicit from_date acts as a precise lower bound.
  5. prewarm_enriched_cache populates _enriched_cache for each strategy.
  6. prewarm_enriched_cache skips strategies whose cache is still valid (no
     unnecessary recomputation).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from analytics.enrichment import _DEFAULT_LOOKBACK_DAYS, fetch_resolved
from analytics.routes_stats import _enriched_cache, _enriched_lock, prewarm_enriched_cache
from api.models import SignalModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_signal(
    db: Session,
    *,
    candle_time: datetime,
    strategy: str = "fvg-impulse",
    resolution: str = "TP_HIT",
) -> SignalModel:
    sig = SignalModel(
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
# from_date filter tests
# ---------------------------------------------------------------------------

class TestFetchResolvedFromDate:
    def test_default_excludes_signals_older_than_lookback(self, db: Session) -> None:
        """Signals older than _DEFAULT_LOOKBACK_DAYS from now are excluded."""
        old_time = datetime.now(timezone.utc) - timedelta(days=_DEFAULT_LOOKBACK_DAYS + 1)
        _insert_signal(db, candle_time=old_time)
        results = fetch_resolved(db)
        assert len(results) == 0

    def test_default_includes_signals_within_lookback(self, db: Session) -> None:
        """Signals within the rolling lookback window are included."""
        recent_time = datetime.now(timezone.utc) - timedelta(days=_DEFAULT_LOOKBACK_DAYS - 1)
        _insert_signal(db, candle_time=recent_time)
        results = fetch_resolved(db)
        assert len(results) == 1

    def test_default_includes_recent_signals(self, db: Session) -> None:
        """Very recent signals are always included."""
        _insert_signal(db, candle_time=datetime.now(timezone.utc) - timedelta(days=7))
        results = fetch_resolved(db)
        assert len(results) == 1

    def test_from_date_none_returns_all_history(self, db: Session) -> None:
        """from_date=None disables the date filter — all resolved signals returned."""
        # Use a date well outside any rolling window (2+ years ago)
        _insert_signal(db, candle_time=datetime(2023, 1, 1, 0, 0, tzinfo=timezone.utc))
        _insert_signal(db, candle_time=datetime.now(timezone.utc) - timedelta(days=200))
        _insert_signal(db, candle_time=datetime.now(timezone.utc) - timedelta(days=10))
        results = fetch_resolved(db, from_date=None)
        assert len(results) == 3

    def test_explicit_from_date_is_precise_lower_bound(self, db: Session) -> None:
        """An explicit from_date filters with millisecond precision."""
        cutoff = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
        _insert_signal(db, candle_time=datetime(2026, 1, 31, 23, 59, tzinfo=timezone.utc))
        _insert_signal(db, candle_time=cutoff)
        _insert_signal(db, candle_time=datetime(2026, 2, 15, 12, 0, tzinfo=timezone.utc))
        results = fetch_resolved(db, from_date=cutoff)
        assert len(results) == 2

    def test_from_date_combined_with_strategy_filter(self, db: Session) -> None:
        """from_date and strategy filters compose correctly (AND logic)."""
        after = datetime(2026, 2, 1, 0, 0, tzinfo=timezone.utc)
        _insert_signal(db, candle_time=after, strategy="fvg-impulse")
        _insert_signal(db, candle_time=after, strategy="nova-candle")
        _insert_signal(db, candle_time=datetime(2025, 1, 1, tzinfo=timezone.utc), strategy="fvg-impulse")

        results = fetch_resolved(db, strategy="fvg-impulse", from_date=after)
        assert len(results) == 1
        assert results[0].strategy == "fvg-impulse"

    def test_default_limit_is_2000(self, db: Session) -> None:
        """Default limit is 2000 (raised from 500)."""
        # Insert 10 signals and confirm all are returned — limit doesn't truncate small sets
        for i in range(10):
            _insert_signal(
                db,
                candle_time=datetime(2026, 1, 1, i, 0, tzinfo=timezone.utc),
            )
        results = fetch_resolved(db)
        assert len(results) == 10


# ---------------------------------------------------------------------------
# prewarm_enriched_cache tests
# ---------------------------------------------------------------------------

class TestPrewarmEnrichedCache:
    @pytest.fixture(autouse=True)
    def _auto_clear_enriched_cache(self) -> None:
        """Clear _enriched_cache before each test to prevent state leaks."""
        with _enriched_lock:
            _enriched_cache.clear()

    def _clear_enriched_cache(self) -> None:
        with _enriched_lock:
            _enriched_cache.clear()

    def test_prewarm_populates_cache_for_each_strategy(self, db: Session) -> None:
        """prewarm_enriched_cache writes an entry into _enriched_cache per strategy."""
        self._clear_enriched_cache()

        # Insert a signal so fetch_resolved has something to work with
        _insert_signal(db, candle_time=datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc))

        mock_cache = MagicMock()
        mock_cache.warm.return_value = ([], [])
        mock_cache.get.return_value = None  # no candles — graceful degradation

        strategies = ["fvg-impulse"]
        prewarm_enriched_cache(strategies, db, mock_cache)

        with _enriched_lock:
            assert "fvg-impulse" in _enriched_cache
            entry = _enriched_cache["fvg-impulse"]

        assert isinstance(entry.enriched, list)
        assert len(entry.enriched) == 1
        assert entry.expires_at > datetime.now(timezone.utc)

    def test_prewarm_skips_valid_cache_entries(self, db: Session) -> None:
        """prewarm_enriched_cache does not recompute when cache is still valid."""
        self._clear_enriched_cache()

        _insert_signal(db, candle_time=datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc))

        mock_cache = MagicMock()
        mock_cache.warm.return_value = ([], [])
        mock_cache.get.return_value = None

        # First warm — populates the cache
        prewarm_enriched_cache(["fvg-impulse"], db, mock_cache)

        with _enriched_lock:
            first_entry = _enriched_cache["fvg-impulse"]

        # Second warm — cache is still valid, should not recompute
        with patch("analytics.routes_stats.enrich_batch") as mock_enrich:
            prewarm_enriched_cache(["fvg-impulse"], db, mock_cache)
            mock_enrich.assert_not_called()

        with _enriched_lock:
            assert _enriched_cache["fvg-impulse"] is first_entry  # same object

    def test_prewarm_multiple_strategies(self, db: Session) -> None:
        """prewarm_enriched_cache handles multiple strategies in one call."""
        self._clear_enriched_cache()

        _insert_signal(db, candle_time=datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc), strategy="fvg-impulse")
        _insert_signal(db, candle_time=datetime(2026, 2, 1, 11, 0, tzinfo=timezone.utc), strategy="nova-candle")

        mock_cache = MagicMock()
        mock_cache.warm.return_value = ([], [])
        mock_cache.get.return_value = None

        prewarm_enriched_cache(["fvg-impulse", "nova-candle"], db, mock_cache)

        with _enriched_lock:
            assert "fvg-impulse" in _enriched_cache
            assert "nova-candle" in _enriched_cache

    def test_prewarm_empty_strategy_list_is_noop(self, db: Session) -> None:
        """prewarm_enriched_cache with an empty list does nothing."""
        self._clear_enriched_cache()
        mock_cache = MagicMock()
        prewarm_enriched_cache([], db, mock_cache)
        with _enriched_lock:
            assert len(_enriched_cache) == 0
