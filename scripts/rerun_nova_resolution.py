"""
scripts/rerun_nova_resolution.py
---------------------------------
One-off script: resets all nova-candle signal resolutions to NULL then
re-runs the resolver so the new two-phase fill-check logic is applied.

Run from the repo root:
    python scripts/rerun_nova_resolution.py
"""
from __future__ import annotations

import logging
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT, ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("rerun-nova")

from api.db import SessionLocal
from api.models import SignalModel
from runner.resolver import resolve_pending_signals


def main() -> None:
    db = SessionLocal()
    try:
        signals = (
            db.query(SignalModel)
            .filter(SignalModel.strategy == "nova-candle")
            .all()
        )
        logger.info("Found %d nova-candle signal(s) — resetting resolutions...", len(signals))

        confirm = input(
            "This will reset resolution for ALL nova-candle signals. Continue? [y/N] "
        ).strip().lower()
        if confirm != "y":
            print("Aborted.")
            sys.exit(0)

        for sig in signals:
            sig.resolution = None
            sig.resolved_at = None
            sig.resolved_price = None
            sig.resolution_candles = None

        db.commit()
        logger.info("Reset complete. Running resolver...")

        resolved = resolve_pending_signals(db)
        logger.info("Done — %d signal(s) resolved.", resolved)
    finally:
        db.close()


if __name__ == "__main__":
    main()
