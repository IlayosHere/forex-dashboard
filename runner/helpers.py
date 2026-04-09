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

SCAN_INTERVAL_SECONDS: int = 5 * 60


def wait_for_next_candle() -> None:
    """Sleep until the next 5-minute candle boundary + 5-second buffer."""
    now = datetime.now(timezone.utc)
    elapsed = (now.minute % 5) * 60 + now.second
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

def discover_strategies() -> dict[str, object]:
    """Return {module_name: scan_callable} for every valid strategy package.

    A valid strategy is a package under strategies/ whose scanner.py exports
    a callable ``scan() -> list[Signal]``.
    """
    found: dict[str, object] = {}
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
    """Return True if a signal for (strategy, symbol, candle_time) already exists."""
    return db.scalar(
        select(SignalModel).where(
            SignalModel.strategy == sig.strategy,
            SignalModel.symbol == sig.symbol,
            SignalModel.direction == sig.direction,
            SignalModel.candle_time == sig.candle_time,
        ),
    ) is not None


def persist(db: Session, sig: Signal) -> None:
    """Insert a Signal into the DB. Skip gracefully on duplicate."""
    try:
        db.add(
            SignalModel(
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
        )
        db.flush()
    except IntegrityError:
        db.rollback()
        logger.info(
            "Duplicate signal skipped: %s %s %s",
            sig.strategy, sig.symbol, sig.candle_time,
        )


