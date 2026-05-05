"""
scripts/enrich_backfill.py
--------------------------
Backfill _analytics_params into resolved signals that pre-date the analytics
enrichment feature. Safe to re-run: signals with existing params are skipped.

Usage:
    python scripts/enrich_backfill.py
    python scripts/enrich_backfill.py --strategy fvg-impulse --dry-run
    python scripts/enrich_backfill.py --from 2026-02-22 --to 2026-03-25
    python scripts/enrich_backfill.py --batch-size 100
"""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
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
logger = logging.getLogger("enrich_backfill")

from analytics.enrichment import ANALYTICS_PARAMS_KEY, enrich_with_candles  # noqa: E402
from api.db import Base, SessionLocal, engine  # noqa: E402
from api.models import SignalModel  # noqa: E402
from sqlalchemy import Text, cast, or_, select  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

Base.metadata.create_all(bind=engine)

_DEFAULT_BATCH_SIZE: int = 200


@dataclass
class EnrichReport:
    """Summary of an enrich_backfill run."""

    dry_run: bool
    processed: int = 0
    params_written: int = 0
    params_partial: int = 0
    no_candle_data: int = 0
    skipped: int = 0


def _query_candidates(
    db: Session,
    strategy: str | None,
    symbol: str | None,
    from_date: datetime | None,
    to_date: datetime | None,
    limit: int,
) -> list[SignalModel]:
    """Fetch resolved signals that are missing _analytics_params."""
    stmt = (
        select(SignalModel)
        .where(SignalModel.resolution.in_(["TP_HIT", "SL_HIT"]))
        .where(
            or_(
                SignalModel.signal_metadata.is_(None),
                cast(SignalModel.signal_metadata, Text).not_like('%"_analytics_params"%'),
            )
        )
    )
    if strategy is not None:
        stmt = stmt.where(SignalModel.strategy == strategy)
    if symbol is not None:
        stmt = stmt.where(SignalModel.symbol == symbol)
    if from_date is not None:
        stmt = stmt.where(SignalModel.candle_time >= from_date)
    if to_date is not None:
        stmt = stmt.where(SignalModel.candle_time < to_date)
    stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def _enrich_group(
    symbol: str,
    strategy: str,
    signals: list[SignalModel],
    db: Session,
    dry_run: bool,
    report: EnrichReport,
) -> None:
    """Enrich one (symbol, strategy) group and merge params into signal_metadata."""
    id_to_model: dict[str, SignalModel] = {s.id: s for s in signals}

    try:
        enriched = enrich_with_candles(signals)
    except Exception:
        logger.exception("enrich_with_candles failed for %s/%s — skipping group", symbol, strategy)
        report.no_candle_data += len(signals)
        return

    if not enriched:
        logger.warning("No enriched rows returned for %s/%s", symbol, strategy)
        report.no_candle_data += len(signals)
        return

    for row in enriched:
        sig_id: str = row["id"]
        sig = id_to_model.get(sig_id)
        if sig is None:
            continue

        params: dict[str, Any] = row.get("params") or {}
        meta = dict(sig.signal_metadata or {})
        meta[ANALYTICS_PARAMS_KEY] = params
        sig.signal_metadata = meta

        is_partial = any(v is None for v in params.values())
        report.processed += 1
        report.params_written += 1
        if is_partial:
            report.params_partial += 1

        logger.info(
            "%s signal %s [%s %s] → wrote %d param(s)%s",
            "DRY-RUN" if dry_run else "ENRICHED",
            sig.id, strategy, symbol,
            len(params),
            " (partial)" if is_partial else "",
        )

    if dry_run:
        db.rollback()
    else:
        db.commit()


def enrich_backfill(
    dry_run: bool = False,
    strategy: str | None = None,
    symbol: str | None = None,
    from_date: datetime | None = None,
    to_date: datetime | None = None,
    limit: int = _DEFAULT_BATCH_SIZE,
) -> EnrichReport:
    """Backfill analytics params for resolved signals missing them.

    dry_run=True runs all computation but rolls back before writing.
    Signals that already have _analytics_params in their metadata are skipped.
    """
    report = EnrichReport(dry_run=dry_run)
    db = SessionLocal()
    try:
        candidates = _query_candidates(db, strategy, symbol, from_date, to_date, limit)
        logger.info("Found %d candidate signal(s) missing analytics params", len(candidates))

        unenriched: list[SignalModel] = []
        for sig in candidates:
            if (sig.signal_metadata or {}).get(ANALYTICS_PARAMS_KEY) is not None:
                report.skipped += 1
                logger.debug("Skipping signal %s — already has params", sig.id)
            else:
                unenriched.append(sig)

        if not unenriched:
            _log_report(report)
            return report

        groups: dict[tuple[str, str], list[SignalModel]] = {}
        for sig in unenriched:
            groups.setdefault((sig.symbol, sig.strategy), []).append(sig)

        for (sym, strat), group_signals in groups.items():
            _enrich_group(sym, strat, group_signals, db, dry_run, report)
    finally:
        db.close()

    _log_report(report)
    return report


def _log_report(report: EnrichReport) -> None:
    """Log a human-readable summary of the enrich run."""
    mode = "DRY-RUN" if report.dry_run else "COMMITTED"
    logger.info(
        "[%s] processed=%d  params_written=%d  params_partial=%d  "
        "no_candle_data=%d  skipped=%d",
        mode,
        report.processed,
        report.params_written,
        report.params_partial,
        report.no_candle_data,
        report.skipped,
    )


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the enrich_backfill script."""
    p = argparse.ArgumentParser(description="Backfill analytics params into resolved signals")
    p.add_argument("--dry-run", action="store_true", help="Do not commit to DB")
    p.add_argument("--strategy", help="Filter to a single strategy slug")
    p.add_argument("--symbol", help="Filter to a single currency pair")
    p.add_argument("--from", dest="from_date", help="Process signals with candle_time >= YYYY-MM-DD")
    p.add_argument("--to", dest="to_date", help="Process signals with candle_time < YYYY-MM-DD")
    p.add_argument("--limit", type=int, default=_DEFAULT_BATCH_SIZE, help="Max signals to process")
    p.add_argument("--batch-size", type=int, dest="batch_size", help="Alias for --limit")
    return p.parse_args()


def main() -> None:
    """CLI entry point for enrich_backfill."""
    args = _parse_args()
    limit = args.batch_size if args.batch_size is not None else args.limit
    from_date = (
        datetime.strptime(args.from_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.from_date else None
    )
    to_date = (
        datetime.strptime(args.to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.to_date else None
    )

    enrich_backfill(
        dry_run=args.dry_run,
        strategy=args.strategy,
        symbol=args.symbol,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )


if __name__ == "__main__":
    main()
