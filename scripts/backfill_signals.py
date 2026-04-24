"""
scripts/backfill_signals.py
---------------------------
One-shot backfill of missed signals between a start date and now.

For each strategy and symbol, fetches enough historical candles, then
replays every candle in the window as if the scanner had run at that
moment -- by patching datetime.now() to return a time just after each
candle closed.  This is the only unbiased approach: the freshness check
and last-closed-index logic both behave exactly as they would have in
production.

No Discord notifications are sent.

Usage (with prod-connect tunnel active):
    DATABASE_URL=postgresql+psycopg2://... python scripts/backfill_signals.py
    DATABASE_URL=postgresql+psycopg2://... python scripts/backfill_signals.py --from 2026-04-18
    python scripts/backfill_signals.py  # SQLite (local dev)
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill")

# Project imports — after sys.path configured
from api.db import Base, SessionLocal, engine  # noqa: E402
from api.models import SignalModel  # noqa: E402
from runner.helpers import is_duplicate, persist  # noqa: E402
from shared.signal import Signal  # noqa: E402

Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Strategy definitions
# ---------------------------------------------------------------------------

# Each entry: (strategy_slug, module_path, candle_interval_minutes, candle_count)
# candle_count must cover the backfill window + enough history for the scanner
# to build FVG state.  FVG strategies use last ~70 bars for state; we add the
# backfill window on top.
_STRATEGIES = [
    ("fvg-impulse",    "strategies.fvg_impulse.scanner",    15, 500),
    ("fvg-impulse-5m", "strategies.fvg_impulse_5m.scanner", 5,  1500),
    ("nova-candle",    "strategies.nova_candle.scanner",     15, 500),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _candle_indices_in_window(
    candles: Any,
    start: datetime,
    end: datetime,
    interval_minutes: int,
) -> list[int]:
    """Return indices of candles whose timestamp falls in [start, end).

    We include a candle at index i only if the candle *closed* (i.e. its
    timestamp is >= start) and strictly before end, AND there are at least
    2 candles before it (index >= 2) so the scanner has context.
    """
    indices = []
    for i, ts in enumerate(candles.index):
        ct = ts.to_pydatetime()
        if ct >= start and ct < end and i >= 2:
            indices.append(i)
    return indices


def _fake_now_for_candle(candle_time: datetime, interval_minutes: int) -> datetime:
    """Return a fake 'now' that is 30 seconds after the candle closed.

    This makes _find_last_closed_index select this candle as the last closed
    one, and makes the freshness check pass (0.5 min << 20/35 min window).
    """
    return candle_time + timedelta(seconds=30)


# ---------------------------------------------------------------------------
# Per-strategy backfill
# ---------------------------------------------------------------------------

def _backfill_fvg(
    scanner_mod: Any,
    slug: str,
    symbol: str,
    candles: Any,
    indices: list[int],
    interval_minutes: int,
) -> list[Signal]:
    """Replay FVG scanner (fvg-impulse or fvg-impulse-5m) for each candle index."""
    results: list[Signal] = []
    # Clear the module-level dedup set so old in-memory state doesn't bleed in
    scanner_mod._alerted_candles.clear()

    for idx in indices:
        candle_time = candles.index[idx].to_pydatetime()
        fake_now = _fake_now_for_candle(candle_time, interval_minutes)

        # Patch datetime.now inside the scanner module so both
        # _find_last_closed_index and the freshness check use fake_now.
        with patch(f"{scanner_mod.__name__}.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            raw_signals = scanner_mod.scan_symbol(candles, symbol)

        for raw in raw_signals:
            results.append(scanner_mod._to_signal(raw))

        # Clear dedup so the next candle isn't blocked by this one
        scanner_mod._alerted_candles.clear()

    return results


def _backfill_nova(
    scanner_mod: Any,
    symbol: str,
    candles: Any,
    indices: list[int],
    interval_minutes: int,
) -> list[Signal]:
    """Replay nova-candle scanner for each candle index."""
    results: list[Signal] = []
    scanner_mod._alerted_candles.clear()

    for idx in indices:
        candle_time = candles.index[idx].to_pydatetime()
        fake_now = _fake_now_for_candle(candle_time, interval_minutes)

        with patch(f"{scanner_mod.__name__}.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = scanner_mod.find_nova_candle(candles, symbol)

        if result is None:
            scanner_mod._alerted_candles.clear()
            continue

        result["symbol"] = symbol
        from strategies.nova_candle.calculations import calculate_trade_params
        trade_params = calculate_trade_params(result, candles, idx)
        if trade_params is None:
            scanner_mod._alerted_candles.clear()
            continue

        result.update(trade_params)
        results.append(scanner_mod._to_signal(result))
        scanner_mod._alerted_candles.clear()

    return results


# ---------------------------------------------------------------------------
# Main backfill loop
# ---------------------------------------------------------------------------

def backfill(start: datetime, end: datetime, dry_run: bool = False) -> None:
    """Run the full backfill from start to end across all strategies."""
    import importlib

    logger.info("Backfill window: %s → %s (dry_run=%s)", start, end, dry_run)

    db = SessionLocal()
    total_inserted = 0
    total_skipped = 0

    try:
        for slug, module_path, interval_minutes, candle_count in _STRATEGIES:
            logger.info("=" * 60)
            logger.info("Strategy: %s  (interval=%dm, fetching %d bars)",
                        slug, interval_minutes, candle_count)

            mod = importlib.import_module(module_path)

            # Read the pairs for this strategy (same env vars as live runner)
            env_key = slug.upper().replace("-", "_") + "_PAIRS"
            pairs_str = os.getenv(env_key, mod.DEFAULT_PAIRS)
            symbols = [p.strip() for p in pairs_str.split(",") if p.strip()]

            strategy_inserted = 0
            strategy_skipped = 0

            for symbol in symbols:
                logger.info("[%s] Fetching candles for %s...", slug, symbol)
                if slug == "nova-candle":
                    from shared.market_data import get_candles as _shared_get_candles
                    from tvDatafeed import Interval
                    candles = _shared_get_candles(symbol, Interval.in_15_minute, candle_count)
                else:
                    candles = mod.get_candles(symbol, candle_count)

                if candles is None:
                    logger.warning("[%s] No candles for %s — skipping", slug, symbol)
                    continue

                indices = _candle_indices_in_window(candles, start, end, interval_minutes)
                if not indices:
                    logger.info("[%s] %s: no candles in window", slug, symbol)
                    continue

                logger.info("[%s] %s: scanning %d candle(s) in window",
                            slug, symbol, len(indices))

                if slug == "nova-candle":
                    signals = _backfill_nova(mod, symbol, candles, indices, interval_minutes)
                else:
                    signals = _backfill_fvg(mod, slug, symbol, candles, indices, interval_minutes)

                for sig in signals:
                    if is_duplicate(db, sig):
                        logger.debug("[%s] Duplicate: %s %s @ %s",
                                     slug, sig.symbol, sig.direction, sig.candle_time)
                        strategy_skipped += 1
                        continue

                    if dry_run:
                        logger.info("[DRY RUN] Would insert: %s %s %s @ %s",
                                    sig.strategy, sig.symbol, sig.direction, sig.candle_time)
                        strategy_inserted += 1
                    else:
                        if persist(db, sig):
                            logger.info("Inserted: %s %s %s @ %s",
                                        sig.strategy, sig.symbol, sig.direction, sig.candle_time)
                            strategy_inserted += 1
                        else:
                            strategy_skipped += 1

                if not dry_run and strategy_inserted > 0:
                    db.commit()

            logger.info("[%s] Done: %d inserted, %d skipped",
                        slug, strategy_inserted, strategy_skipped)
            total_inserted += strategy_inserted
            total_skipped += strategy_skipped

    finally:
        db.close()

    logger.info("=" * 60)
    logger.info("Backfill complete: %d inserted, %d skipped", total_inserted, total_skipped)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill missed signals into the DB.")
    parser.add_argument(
        "--from",
        dest="start",
        default="2026-04-18",
        help="Start date (UTC, inclusive) in YYYY-MM-DD format. Default: 2026-04-18",
    )
    parser.add_argument(
        "--to",
        dest="end",
        default=None,
        help="End date (UTC, exclusive) in YYYY-MM-DD format. Default: now",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be inserted without writing to the DB.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    start_dt = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = (
        datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.end
        else datetime.now(timezone.utc)
    )

    backfill(start_dt, end_dt, dry_run=args.dry_run)
