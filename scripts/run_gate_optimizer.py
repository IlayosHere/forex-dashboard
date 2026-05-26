"""
scripts/run_gate_optimizer.py
------------------------------
Standalone runner for the gate auto-optimizer.

Calls the optimizer directly against the DB (no HTTP, no auth needed).
Designed to be run weekly as a scheduled job or manually.

Usage:
    # Dry-run (shows what gate would be created, writes nothing):
    python scripts/run_gate_optimizer.py --strategy fvg-impulse --dry-run

    # Live run against local SQLite:
    python scripts/run_gate_optimizer.py --strategy fvg-impulse

    # Live run against prod (with DATABASE_URL set):
    DATABASE_URL=postgresql+psycopg2://forex:<pw>@127.0.0.1:5433/forex \\
        python scripts/run_gate_optimizer.py --strategy fvg-impulse

    # Also recompute grades after optimizing:
    python scripts/run_gate_optimizer.py --strategy fvg-impulse --recompute-grades
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gate-optimizer")

_MIN_PASS_RATE = 0.40
_AUTO_NAME_PREFIX = "Auto-optimized"
_A_MIN_DEFAULT = 60
_B_MIN_DEFAULT = 20


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run gate auto-optimizer")
    p.add_argument("--strategy", required=True, help="Strategy slug, e.g. fvg-impulse")
    p.add_argument("--min-pass-rate", type=float, default=_MIN_PASS_RATE)
    p.add_argument("--dry-run", action="store_true", help="Show result without writing to DB")
    p.add_argument("--recompute-grades", action="store_true", help="Recompute A/B/C/D grades after optimizing")
    return p.parse_args()


def _create_and_activate(db, strategy: str, conditions: list) -> str:
    from sqlalchemy import select
    from api.models_gates import GateSetModel

    now = datetime.now(timezone.utc)
    gate_set_id = str(uuid4())

    for other in db.scalars(
        select(GateSetModel).where(
            GateSetModel.strategy == strategy,
            GateSetModel.is_active.is_(True),
        )
    ).all():
        other.is_active = False

    db.add(GateSetModel(
        id=gate_set_id,
        strategy=strategy,
        name=f"{_AUTO_NAME_PREFIX} {now.strftime('%Y-%m-%d')}",
        description="Created by auto-optimizer script",
        is_active=True,
        conditions=conditions,
        created_at=now,
        updated_at=now,
    ))
    db.commit()
    return gate_set_id


def _recompute_grades(db, strategy: str) -> int:
    from sqlalchemy import select
    from analytics.confirmed_cache import get_confirmed_params
    from analytics.enrichment import enrich_batch, fetch_resolved
    from analytics.scoring import compute_score
    from api.models import SignalModel
    from api.models_gates import GradeThresholdsModel

    thresholds = db.scalar(
        select(GradeThresholdsModel).where(
            GradeThresholdsModel.strategy == strategy,
            GradeThresholdsModel.is_active.is_(True),
        )
    )
    a_min = thresholds.a_min if thresholds else _A_MIN_DEFAULT
    b_min = thresholds.b_min if thresholds else _B_MIN_DEFAULT

    signals_all = fetch_resolved(db, strategy=strategy)
    enriched = enrich_batch(signals_all)
    confirmed = get_confirmed_params(enriched, strategy)

    all_signals = list(db.scalars(
        select(SignalModel).where(SignalModel.strategy == strategy)
    ).all())

    changed = 0
    for sig in all_signals:
        result = compute_score(sig, strategy, candles=None, confirmed_params=confirmed)
        score = int(result["score"])
        max_possible = int(result["max_possible"])
        grade = _classify(score, max_possible, a_min, b_min)
        if sig.grade != grade or sig.score_snapshot != score:
            sig.grade = grade
            sig.score_snapshot = score
            sig.score_max_snapshot = max_possible
            changed += 1

    db.commit()
    return changed


def _classify(score: int, max_possible: int, a_min: int, b_min: int) -> str | None:
    if max_possible == 0:
        return None
    n = max(-100, min(100, round(100 * score / max_possible)))
    if n >= a_min:
        return "A"
    if n >= b_min:
        return "B"
    return "C" if n >= 0 else "D"


def main() -> None:
    args = _parse_args()

    import api.models_gates  # noqa: F401 — registers models with Base
    from analytics.candle_cache import CandleCache
    from api.db import Base, SessionLocal, engine
    from api.models import SignalModel  # noqa: F401

    Base.metadata.create_all(bind=engine)

    from api.services.gate_optimizer_runner import run_optimizer

    db = SessionLocal()
    cache = CandleCache()
    try:
        logger.info("Running gate optimizer: strategy=%s min_pass_rate=%.2f dry_run=%s",
                    args.strategy, args.min_pass_rate, args.dry_run)

        result = run_optimizer(db, args.strategy, cache, args.min_pass_rate)

        logger.info("Baseline win rate:   %.1f%%", (result.get("win_rate_baseline") or 0) * 100)
        logger.info("Optimized win rate:  %.1f%%", (result.get("win_rate_optimized") or 0) * 100)
        logger.info("Delta vs baseline:   %+.1f%%", (result.get("delta") or 0) * 100)
        logger.info("Pass rate:           %.1f%%", (result.get("pass_rate") or 0) * 100)
        logger.info("Pass count:          %d / %d", result["pass_count"], result["total_signals"])
        logger.info("Confirmed params:    %d", result["confirmed_params_found"])
        logger.info("Conditions selected: %s", result["conditions_selected"])

        if result.get("reason"):
            logger.warning("No gate created — reason: %s", result["reason"])
        elif result["conditions_selected"] and not args.dry_run:
            gate_id = _create_and_activate(db, args.strategy, result["conditions_selected"])
            logger.info("Gate activated: id=%s", gate_id)
        elif args.dry_run:
            logger.info("[dry-run] Gate would have been created with %d condition(s)",
                        len(result["conditions_selected"]))

        if args.recompute_grades and not args.dry_run:
            changed = _recompute_grades(db, args.strategy)
            logger.info("Grades recomputed: %d signal(s) updated", changed)

    finally:
        db.close()


if __name__ == "__main__":
    main()
