"""
scripts/backfill_tp_target_taxonomy.py
----------------------------------------
One-shot backfill of trades.ict_tp_target (and the new ict_tp_target_detail column)
from the old flat TP-target taxonomy to the new type+detail taxonomy.

Old -> new mapping:
  - london_high/low, asia_high/low, ath, other -> unchanged (no-op)
  - 1d_high/low            -> pdh/pdl
  - data_high/low          -> data_release_high/low (tp_target_detail left NULL — the
                               release type (CPI/PPI/NFP/FOMC) can't be recovered
                               retroactively for historical trades)
  - {1m,5m,15m,1h,4h}_high -> tp_target=ith, tp_target_detail=<timeframe>
                               (1m folded into 5m — no dedicated 1-minute bucket in
                               the new swing-structure taxonomy)
  - {1m,5m,15m,1h,4h}_low  -> tp_target=itl, tp_target_detail=<timeframe> (1m -> 5m)
  - unmitigated_{5m,15m,30m,1h,4h}_fvg -> tp_target=unmitigated_fvg, tp_target_detail=<tf>

Requires the ict_tp_target_detail column to already exist — run this after the schema
migration (migrate_add_ict_tp_target_detail_column in api/startup/migrations.py), and
on prod, only after that ALTER has been pre-applied manually per CLAUDE.md
§Production Migration Safety.

Usage:
    # Dry-run (prints what would change, writes nothing):
    python scripts/backfill_tp_target_taxonomy.py --dry-run

    # Live run against local SQLite:
    python scripts/backfill_tp_target_taxonomy.py

    # Live run against prod (with prod-connect tunnel open):
    DATABASE_URL=postgresql+psycopg2://forex:<password>@127.0.0.1:5433/forex \\
        python scripts/backfill_tp_target_taxonomy.py
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill-tp-target")

from api.db import SessionLocal
from api.models import TradeModel

# tp_target values that carry no meaning change — no write needed.
_UNCHANGED = {"london_high", "london_low", "asia_high", "asia_low", "ath", "other"}

# Direct rename, no detail.
_DIRECT_RENAME: dict[str, str] = {
    "1d_high": "pdh",
    "1d_low": "pdl",
    "data_high": "data_release_high",
    "data_low": "data_release_low",
}

# Old "<tf>_high" -> new tp_target="ith", tp_target_detail=<tf>.
_ITH_DETAIL_RENAME: dict[str, str] = {
    "1m_high": "5m",
    "5m_high": "5m",
    "15m_high": "15m",
    "1h_high": "1h",
    "4h_high": "4h",
}

# Old "<tf>_low" -> new tp_target="itl", tp_target_detail=<tf>.
_ITL_DETAIL_RENAME: dict[str, str] = {
    "1m_low": "5m",
    "5m_low": "5m",
    "15m_low": "15m",
    "1h_low": "1h",
    "4h_low": "4h",
}

# Old "unmitigated_<tf>_fvg" -> new tp_target="unmitigated_fvg", tp_target_detail=<tf>.
_FVG_DETAIL_RENAME: dict[str, str] = {
    "unmitigated_5m_fvg": "5m",
    "unmitigated_15m_fvg": "15m",
    "unmitigated_30m_fvg": "30m",
    "unmitigated_1h_fvg": "1h",
    "unmitigated_4h_fvg": "4h",
}


def _resolve(old_value: str) -> tuple[str, str | None] | None:
    """Return (new_tp_target, new_tp_target_detail) for an old value, or None if no rename is needed."""
    if old_value in _DIRECT_RENAME:
        return _DIRECT_RENAME[old_value], None
    if old_value in _ITH_DETAIL_RENAME:
        return "ith", _ITH_DETAIL_RENAME[old_value]
    if old_value in _ITL_DETAIL_RENAME:
        return "itl", _ITL_DETAIL_RENAME[old_value]
    if old_value in _FVG_DETAIL_RENAME:
        return "unmitigated_fvg", _FVG_DETAIL_RENAME[old_value]
    return None


def backfill(dry_run: bool = False) -> None:
    """Rewrite every trades.ict_tp_target still on the old taxonomy to the new one."""
    db = SessionLocal()
    updated = 0
    unchanged = 0
    unmapped = 0
    try:
        trades = list(db.query(TradeModel).filter(TradeModel.ict_tp_target.isnot(None)).all())
        logger.info("Found %d trades with ict_tp_target set", len(trades))

        for trade in trades:
            if trade.ict_tp_target in _UNCHANGED:
                unchanged += 1
                continue

            resolved = _resolve(trade.ict_tp_target)
            if resolved is None:
                unmapped += 1
                logger.warning(
                    "  trade %s: no mapping for ict_tp_target=%r — left untouched, review manually",
                    trade.id, trade.ict_tp_target,
                )
                continue

            new_target, new_detail = resolved
            logger.info(
                "  trade %s: %r -> tp_target=%r, tp_target_detail=%r",
                trade.id, trade.ict_tp_target, new_target, new_detail,
            )
            if not dry_run:
                trade.ict_tp_target = new_target
                trade.ict_tp_target_detail = new_detail
            updated += 1

        if not dry_run and updated > 0:
            db.commit()
    finally:
        db.close()

    logger.info("=" * 60)
    logger.info("Backfill complete:")
    logger.info("  Updated:            %d trades", updated)
    logger.info("  Already valid:      %d trades (london/asia/ath/other)", unchanged)
    logger.info("  Unmapped (skipped): %d trades", unmapped)
    if dry_run:
        logger.info("  ** DRY RUN — nothing written to DB **")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill trades.ict_tp_target to the new type+detail taxonomy.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing to DB.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    backfill(dry_run=args.dry_run)
