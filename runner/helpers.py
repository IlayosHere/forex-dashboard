"""
runner/helpers.py
-----------------
Helper functions extracted from runner/main.py: strategy discovery,
DB persistence (with gate + grade evaluation), and market-hours logic.
"""
from __future__ import annotations

import importlib
import logging
import os
import pkgutil
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from analytics.candle_cache import CandleCache
from analytics.signal_enricher import compute_and_attach
from api.models import SignalModel
from runner.gate_runner import GateDecision, evaluate_gate_for_signal
from runner.grade_runner import GradeDecision, compute_grade_for_signal
from shared.signal import Signal

logger = logging.getLogger("Runner")

_STRATEGIES_DIR: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "strategies",
)


# ---------------------------------------------------------------------------
# Market hours
# ---------------------------------------------------------------------------

def is_market_open() -> bool:
    """Return True if the forex market is open (Sun 22:00 UTC - Fri 22:00 UTC)."""
    now = datetime.now(timezone.utc)
    day = now.weekday()  # Mon=0 ... Sun=6
    hour = now.hour
    if day == 4 and hour >= 22:  # Friday 22:00+
        return False
    if day == 5:  # Saturday
        return False
    if day == 6 and hour < 22:  # Sunday before 22:00 UTC
        return False
    return True


# ---------------------------------------------------------------------------
# Candle timing
# ---------------------------------------------------------------------------

SCAN_INTERVAL_SECONDS: int = int(os.getenv("SCAN_INTERVAL_SECONDS", str(5 * 60)))


def wait_for_next_candle() -> None:
    """Sleep until the next candle boundary + 5-second buffer."""
    interval_minutes: int = max(1, SCAN_INTERVAL_SECONDS // 60)
    now = datetime.now(timezone.utc)
    elapsed = (now.minute % interval_minutes) * 60 + now.second
    seconds_to_wait = SCAN_INTERVAL_SECONDS - elapsed + 5
    if seconds_to_wait <= 5:
        seconds_to_wait += SCAN_INTERVAL_SECONDS
    next_time = datetime.fromtimestamp(now.timestamp() + seconds_to_wait, tz=timezone.utc)
    logger.info(
        "Next scan at %s (in %ds)",
        next_time.strftime("%H:%M:%S UTC"),
        seconds_to_wait,
    )
    time.sleep(seconds_to_wait)


# ---------------------------------------------------------------------------
# Strategy discovery
# ---------------------------------------------------------------------------

def discover_strategies() -> dict[str, Callable[[], list[Signal]]]:
    """Return {slug: scan_callable} for every valid strategy package.

    A valid strategy is a package under strategies/ whose scanner.py exports
    a callable ``scan() -> list[Signal]``.
    """
    found: dict[str, Callable[[], list[Signal]]] = {}
    for _finder, name, is_pkg in pkgutil.iter_modules([_STRATEGIES_DIR]):
        if not is_pkg:
            continue
        module_path = f"strategies.{name}.scanner"
        try:
            mod = importlib.import_module(module_path)
        except Exception:
            logger.exception("Failed to import %s -- skipping", module_path)
            continue
        if not callable(getattr(mod, "scan", None)):
            logger.warning("%s has no scan() function -- skipping", module_path)
            continue
        slug = name.replace("_", "-")
        found[slug] = mod.scan
        logger.info("Registered strategy: %s", slug)
    return found


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PersistResult:
    """Outcome of persisting one signal."""

    inserted: bool
    gate_status: str  # "passed" | "blocked" | "no_gates" | "error"
    grade: str | None


def is_duplicate(db: Session, sig: Signal) -> bool:
    """Return True if a signal for (strategy, symbol, candle_time) already exists."""
    return db.scalar(
        select(SignalModel).where(
            SignalModel.strategy == sig.strategy,
            SignalModel.symbol == sig.symbol,
            SignalModel.candle_time == sig.candle_time,
        ),
    ) is not None


def persist(
    db: Session,
    sig: Signal,
    candle_cache: CandleCache | None = None,
    enriched_snapshot: list[dict] | None = None,
) -> PersistResult:
    """Insert a Signal into the DB with gate and grade evaluation.

    Analytics params are computed first (if candle_cache provided), then gate
    conditions are evaluated, then the quality grade is computed. All results
    are persisted together.

    Returns a PersistResult with inserted=False on any IntegrityError, but gate
    and grade are still computed so callers can act on them even on duplicates.
    """
    if candle_cache is not None:
        compute_and_attach(sig, candle_cache)

    gate: GateDecision = evaluate_gate_for_signal(db, sig)
    grade: GradeDecision = compute_grade_for_signal(
        db, sig, enriched_snapshot or [],
    )

    signal_model = _build_signal_model(sig, gate, grade)
    inserted = _insert_with_savepoint(db, signal_model, sig)
    return PersistResult(
        inserted=inserted,
        gate_status=gate.status,
        grade=grade.grade,
    )


def _build_signal_model(
    sig: Signal,
    gate: GateDecision,
    grade: GradeDecision,
) -> SignalModel:
    """Construct a SignalModel from a Signal + gate/grade decisions."""
    return SignalModel(
        id=sig.id,
        strategy=sig.strategy,
        symbol=sig.symbol,
        direction=sig.direction,
        candle_time=sig.candle_time,
        entry=sig.entry,
        sl=sig.sl,
        tp=sig.tp,
        lot_size=sig.lot_size,
        risk_pips=sig.risk_pips,
        spread_pips=sig.spread_pips,
        signal_metadata=sig.metadata,
        created_at=sig.created_at,
        gate_status=gate.status,
        gate_block_reason=gate.block_reason,
        gate_set_id=gate.gate_set_id,
        grade=grade.grade,
        score_snapshot=grade.score,
        score_max_snapshot=grade.max_possible,
    )


def _insert_with_savepoint(db: Session, model: SignalModel, sig: Signal) -> bool:
    """Attempt to insert model; return False on IntegrityError without aborting session."""
    try:
        with db.begin_nested():  # savepoint — rollback only undoes this signal
            db.add(model)
            db.flush()
    except IntegrityError as e:
        orig_msg = str(e.orig).upper()
        is_dup = "UNIQUE" in orig_msg or "DUPLICATE KEY" in orig_msg or "23505" in orig_msg
        if is_dup:
            logger.info(
                "Duplicate signal skipped: %s %s %s",
                sig.strategy, sig.symbol, sig.candle_time,
            )
        else:
            logger.error(
                "IntegrityError persisting signal %s (non-duplicate): %s",
                sig.id, e, exc_info=True,
            )
        return False
    return True
