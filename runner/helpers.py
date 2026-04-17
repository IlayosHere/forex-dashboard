"""
runner/helpers.py
-----------------
Helper functions extracted from runner/main.py: strategy discovery,
DB persistence, and market-hours logic.
"""
from __future__ import annotations

import importlib
import logging
import os
import pkgutil
import time
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.models import SignalModel
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
    """Return {module_name: scan_callable} for every valid strategy package.

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

def is_duplicate(db: Session, sig: Signal) -> bool:
    """Return True if a signal for (strategy, symbol, candle_time) already exists.

    Matches the DB unique constraint on (strategy, symbol, candle_time).
    direction is intentionally excluded: if a strategy emits BUY and SELL for
    the same candle, the second insert would violate the constraint regardless
    of direction, so we catch it here rather than letting it fail silently.
    """
    return db.scalar(
        select(SignalModel).where(
            SignalModel.strategy == sig.strategy,
            SignalModel.symbol == sig.symbol,
            SignalModel.candle_time == sig.candle_time,
        ),
    ) is not None


def persist(db: Session, sig: Signal) -> bool:
    """Insert a Signal into the DB. Skip gracefully on duplicate.

    Uses a savepoint (``db.begin_nested()``) so that an IntegrityError on this
    signal only rolls back this insert, not the entire session. Previously
    flushed signals in the same cycle are preserved and the outer commit still
    succeeds for all successful inserts.

    Returns True if the signal was inserted, False on any IntegrityError.
    """
    signal_model = SignalModel(
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
    )
    try:
        with db.begin_nested():  # savepoint — rollback only undoes this signal
            db.add(signal_model)
            db.flush()
    except IntegrityError as e:
        orig_msg = str(e.orig).upper()
        _is_dup_error = "UNIQUE" in orig_msg or "DUPLICATE KEY" in orig_msg or "23505" in orig_msg
        if _is_dup_error:
            logger.info("Duplicate signal skipped: %s %s %s", sig.strategy, sig.symbol, sig.candle_time)
        else:
            logger.error(
                "IntegrityError persisting signal %s (non-duplicate): %s",
                sig.id, e, exc_info=True,
            )
        return False
    return True


