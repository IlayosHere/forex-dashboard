"""
scripts/resolve_backfill.py
---------------------------
Resolve historical backfill signals by replaying price action against
fetched candles. Complements the live resolver (runner/resolver.py) for
the one-time use-case of resolving thousands of old backfill signals that
pre-date the live resolver's 500-bar cap.

Usage:
    python scripts/resolve_backfill.py
    python scripts/resolve_backfill.py --dry-run
    python scripts/resolve_backfill.py --strategy fvg-impulse
    python scripts/resolve_backfill.py --run-id backfill-prod-fvg-20260222
    python scripts/resolve_backfill.py --from 2026-02-22 --to 2026-03-25
    python scripts/resolve_backfill.py --strict
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("resolve_backfill")

from analytics.candle_cache import interval_for_strategy  # noqa: E402
from api.db import Base, SessionLocal, engine  # noqa: E402
from api.models import SignalModel  # noqa: E402
from runner.resolution_strategies import MAX_RESOLUTION_CANDLES  # noqa: E402
from runner.resolver import _resolve_signal  # noqa: E402
from shared.market_data import get_candles  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from tvDatafeed import Interval  # noqa: E402

Base.metadata.create_all(bind=engine)

_INTERVAL_SECONDS: dict[Interval, int] = {
    Interval.in_5_minute:  5 * 60,
    Interval.in_15_minute: 15 * 60,
}
_DEFAULT_INTERVAL_SECONDS: int = 15 * 60
_FETCH_BUFFER_BARS: int = 50


@dataclass
class BackfillResolveReport:
    """Summary of a resolve_backfill run."""

    run_id: str | None
    dry_run: bool
    resolved: int = 0
    skipped: int = 0
    no_data: int = 0
    per_strategy: dict[str, dict[str, int]] = field(default_factory=dict)


def _query_unresolved_backfill(
    db: Session,
    strategies: list[str] | None,
    run_id: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
) -> list[SignalModel]:
    """Fetch all unresolved backfill signals matching the given filters."""
    stmt = select(SignalModel).where(SignalModel.resolution.is_(None))
    if from_date is not None:
        stmt = stmt.where(SignalModel.candle_time >= from_date)
    if to_date is not None:
        stmt = stmt.where(SignalModel.candle_time < to_date)
    if strategies:
        stmt = stmt.where(SignalModel.strategy.in_(strategies))
    rows: list[SignalModel] = list(db.scalars(stmt).all())
    filtered = [
        r for r in rows
        if (r.signal_metadata or {}).get("backfill") is True
        and (run_id is None or (r.signal_metadata or {}).get("backfill_run_id") == run_id)
    ]
    return filtered


def _bars_for_group(signals: list[SignalModel], strategy: str) -> int:
    """Compute bar count needed to cover the oldest signal — no 500-bar cap."""
    interval = interval_for_strategy(strategy)
    bar_seconds = _INTERVAL_SECONDS.get(interval, _DEFAULT_INTERVAL_SECONDS)
    now = datetime.now(timezone.utc)
    oldest = min(s.candle_time for s in signals)
    if oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=timezone.utc)
    elapsed = (now - oldest).total_seconds()
    return math.ceil(elapsed / bar_seconds) + MAX_RESOLUTION_CANDLES + _FETCH_BUFFER_BARS


def _resolve_group(
    symbol: str,
    strategy: str,
    signals: list[SignalModel],
    db: Session,
    dry_run: bool,
    strict: bool,
    report: BackfillResolveReport,
) -> None:
    """Fetch candles and resolve all signals in one (symbol, strategy) group."""
    interval = interval_for_strategy(strategy)
    count = _bars_for_group(signals, strategy)
    df = get_candles(symbol, interval, count=count)

    bucket = report.per_strategy.setdefault(strategy, {"resolved": 0, "skipped": 0, "no_data": 0})

    if df is None:
        logger.warning("No candle data for %s @ %s — skipping %d signal(s)", symbol, strategy, len(signals))
        report.no_data += len(signals)
        bucket["no_data"] += len(signals)
        return

    group_resolved = 0
    for sig in signals:
        if strict and sig.candle_time not in df.index:
            raise RuntimeError(
                f"STRICT: candle_time {sig.candle_time} not in fetched DataFrame "
                f"for {symbol} @ {strategy} (signal id={sig.id})"
            )

        resolved = _resolve_signal(sig, df)
        if resolved:
            group_resolved += 1
            logger.info(
                "Resolved %s [%s %s %s] → %s in %s candles",
                sig.id, sig.strategy, sig.symbol, sig.direction,
                sig.resolution, sig.resolution_candles,
            )
        else:
            report.skipped += 1
            bucket["skipped"] += 1
            logger.debug("Skipped (no candle match) signal %s", sig.id)

    if group_resolved and not dry_run:
        db.commit()
    elif group_resolved and dry_run:
        db.rollback()

    report.resolved += group_resolved
    bucket["resolved"] += group_resolved


def resolve_backfill(
    dry_run: bool = False,
    strict: bool = False,
    strategies: list[str] | None = None,
    run_id: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
) -> BackfillResolveReport:
    """Resolve all unresolved backfill signals grouped by (symbol, strategy).

    dry_run=True runs all logic but skips DB commits.
    strict=True aborts with RuntimeError if a signal's candle_time is absent
    from the fetched DataFrame.
    """
    report = BackfillResolveReport(run_id=run_id, dry_run=dry_run)
    db = SessionLocal()
    try:
        signals = _query_unresolved_backfill(db, strategies, run_id, from_date, to_date)
        logger.info("Found %d unresolved backfill signal(s) to process", len(signals))
        if not signals:
            return report

        groups: dict[tuple[str, str], list[SignalModel]] = {}
        for sig in signals:
            groups.setdefault((sig.symbol, sig.strategy), []).append(sig)

        for (symbol, strategy), group_signals in groups.items():
            _resolve_group(symbol, strategy, group_signals, db, dry_run, strict, report)
    finally:
        db.close()

    _log_report(report)
    return report


def _log_report(report: BackfillResolveReport) -> None:
    """Log a human-readable summary of the resolve run."""
    mode = "DRY-RUN" if report.dry_run else "COMMITTED"
    logger.info("[%s] resolved=%d  skipped=%d  no_data=%d", mode, report.resolved, report.skipped, report.no_data)
    for strat, c in report.per_strategy.items():
        logger.info("  %-20s resolved=%d skipped=%d no_data=%d", strat, c["resolved"], c["skipped"], c["no_data"])


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the resolve_backfill script."""
    p = argparse.ArgumentParser(description="Resolve historical backfill signals")
    p.add_argument("--dry-run", action="store_true", help="Do not commit to DB")
    p.add_argument("--strict", action="store_true", help="Abort on data integrity errors")
    p.add_argument("--strategy", help="Comma-separated strategy slugs to process")
    p.add_argument("--run-id", help="Filter to a specific backfill_run_id")
    p.add_argument("--from", dest="from_date", help="Process signals with candle_time >= YYYY-MM-DD")
    p.add_argument("--to", dest="to_date", help="Process signals with candle_time < YYYY-MM-DD")
    return p.parse_args()


def main() -> None:
    """CLI entry point for resolve_backfill."""
    args = _parse_args()
    strategies = [s.strip() for s in args.strategy.split(",")] if args.strategy else None
    from_date = datetime.strptime(args.from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) if args.from_date else None
    to_date = datetime.strptime(args.to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) if args.to_date else None

    try:
        resolve_backfill(
            dry_run=args.dry_run,
            strict=args.strict,
            strategies=strategies,
            run_id=args.run_id,
            from_date=from_date,
            to_date=to_date,
        )
    except RuntimeError as exc:
        logger.error("Aborting: %s", exc)
        sys.exit(2)


if __name__ == "__main__":
    main()
