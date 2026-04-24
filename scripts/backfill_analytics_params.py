"""
scripts/backfill_analytics_params.py
-------------------------------------
One-shot backfill of analytics params for historical signals.

For each unique (symbol, strategy) pair, fetches the maximum available candle
history from TradingView (~5000 M15 bars, ~52 calendar days), then for every
signal in the DB whose candle_time falls within that window AND which has no
pre-computed analytics params, runs resolve_all_params and writes the result
into signal_metadata["_analytics_params"].

Signals outside the candle window (older than ~52 days) are permanently
skipped — their candle data no longer exists.

Usage:
    # Dry-run (prints what would be updated, writes nothing):
    python scripts/backfill_analytics_params.py --dry-run

    # Live run against local SQLite:
    python scripts/backfill_analytics_params.py

    # Live run against prod (with prod-connect tunnel open):
    DATABASE_URL=postgresql+psycopg2://forex:<password>@127.0.0.1:5433/forex \\
        python scripts/backfill_analytics_params.py
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill-analytics")

import analytics.params  # noqa: F401 — triggers @register side-effects

from analytics.candle_cache import interval_for_strategy
from analytics.registry import resolve_all_params
from analytics.signal_enricher import ANALYTICS_PARAMS_KEY
from api.db import Base, SessionLocal, engine
from api.models import SignalModel
from shared.market_data import get_candles

Base.metadata.create_all(bind=engine)

# Fetch the maximum bars tvDatafeed will return per request.
# TradingView server cap is ~5000 bars regardless of what we ask for.
_FETCH_BAR_COUNT = 5000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_candles_for_pair(symbol: str, strategy: str) -> Any:
    """Fetch max available candle history for (symbol, strategy)."""
    interval = interval_for_strategy(strategy)
    logger.info("Fetching %d bars for %s / %s (%s)...", _FETCH_BAR_COUNT, symbol, strategy, interval)
    candles = get_candles(symbol, interval, count=_FETCH_BAR_COUNT)
    if candles is None or candles.empty:
        logger.warning("No candles returned for %s / %s — skipping pair", symbol, strategy)
        return None
    oldest = candles.index[0]
    newest = candles.index[-1]
    logger.info("  Got %d bars: %s → %s", len(candles), oldest, newest)
    return candles


def _signals_needing_backfill(
    db: Any,
    symbol: str,
    strategy: str,
    candle_start: datetime,
) -> list[SignalModel]:
    """Return resolved signals for (symbol, strategy) within the candle window that lack params."""
    from sqlalchemy import select
    stmt = (
        select(SignalModel)
        .where(
            SignalModel.symbol == symbol,
            SignalModel.strategy == strategy,
            SignalModel.resolution.in_(["TP_HIT", "SL_HIT"]),
            SignalModel.candle_time >= candle_start,
        )
        .order_by(SignalModel.candle_time)
    )
    signals = list(db.scalars(stmt).all())
    # Filter to only those without pre-computed params
    return [s for s in signals if ANALYTICS_PARAMS_KEY not in (s.signal_metadata or {})]


def _compute_params(signal: SignalModel, candles: Any) -> dict[str, Any]:
    """Run all registered params for a signal against the provided candles."""
    return resolve_all_params(signal, signal.strategy, candles=candles)


def _log_param_summary(params: dict[str, Any]) -> None:
    non_null = sum(1 for v in params.values() if v is not None)
    logger.info("    %d / %d params non-null", non_null, len(params))


# ---------------------------------------------------------------------------
# Main backfill
# ---------------------------------------------------------------------------

def backfill(dry_run: bool = False) -> None:
    """Run analytics param backfill for all (symbol, strategy) pairs in the DB."""
    db = SessionLocal()
    total_updated = 0
    total_skipped_no_candles = 0
    total_skipped_outside_window = 0

    try:
        # Discover all unique (symbol, strategy) pairs with resolved signals
        from sqlalchemy import select, distinct
        pairs_query = (
            select(distinct(SignalModel.symbol), SignalModel.strategy)
            .where(SignalModel.resolution.in_(["TP_HIT", "SL_HIT"]))
        )
        pairs: list[tuple[str, str]] = list(db.execute(pairs_query).fetchall())
        logger.info("Found %d unique (symbol, strategy) pairs with resolved signals", len(pairs))

        for symbol, strategy in pairs:
            logger.info("=" * 60)
            logger.info("Processing: %s / %s", symbol, strategy)

            candles = _fetch_candles_for_pair(symbol, strategy)
            if candles is None:
                total_skipped_no_candles += 1
                continue

            candle_start = candles.index[0].to_pydatetime()
            if candle_start.tzinfo is None:
                candle_start = candle_start.replace(tzinfo=timezone.utc)

            signals = _signals_needing_backfill(db, symbol, strategy, candle_start)
            logger.info("  %d signal(s) need backfill within candle window", len(signals))

            # Count signals outside the window (informational only)
            from sqlalchemy import func
            total_resolved = db.scalar(
                select(func.count()).select_from(SignalModel).where(
                    SignalModel.symbol == symbol,
                    SignalModel.strategy == strategy,
                    SignalModel.resolution.in_(["TP_HIT", "SL_HIT"]),
                )
            ) or 0
            outside = total_resolved - len(signals)
            if outside > 0:
                total_skipped_outside_window += outside
                logger.info("  %d signal(s) older than candle window — permanently skipped", outside)

            pair_updated = 0
            for signal in signals:
                params = _compute_params(signal, candles)
                non_null = sum(1 for v in params.values() if v is not None)

                if dry_run:
                    logger.info(
                        "  [DRY RUN] %s @ %s — %d/%d params non-null",
                        signal.direction, signal.candle_time, non_null, len(params),
                    )
                    pair_updated += 1
                    continue

                # Merge into existing metadata (preserves existing keys)
                meta = dict(signal.signal_metadata or {})
                meta[ANALYTICS_PARAMS_KEY] = params
                signal.signal_metadata = meta
                pair_updated += 1

                logger.info(
                    "  Updated %s %s @ %s — %d/%d params non-null",
                    signal.symbol, signal.direction, signal.candle_time, non_null, len(params),
                )

            if not dry_run and pair_updated > 0:
                db.commit()

            total_updated += pair_updated
            logger.info("  Pair done: %d updated", pair_updated)

    finally:
        db.close()

    logger.info("=" * 60)
    logger.info("Backfill complete:")
    logger.info("  Updated:                  %d signals", total_updated)
    logger.info("  Skipped (no candles):     %d pairs", total_skipped_no_candles)
    logger.info("  Skipped (outside window): %d signals (candle data gone)", total_skipped_outside_window)
    if dry_run:
        logger.info("  ** DRY RUN — nothing written to DB **")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill analytics params for historical signals.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be updated without writing to DB.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    backfill(dry_run=args.dry_run)
