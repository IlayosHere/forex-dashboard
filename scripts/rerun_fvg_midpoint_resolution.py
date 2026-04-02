"""
scripts/rerun_fvg_midpoint_resolution.py
-----------------------------------------
One-off script: clears and re-computes resolution_midpoint for all fvg-impulse
signals that have sl_midpoint in their metadata.

Fixes a bug where _resolve_midpoint used signal.tp (the far-edge TP) for the TP
check instead of the correct midpoint TP (2 * entry - sl_midpoint).  Signals that
hit the tighter midpoint TP but not the far-edge TP were recorded as EXPIRED
instead of TP_HIT.

Only the midpoint resolution fields (resolution_midpoint, resolution_midpoint_candles)
are touched.  Far-edge resolution (resolution, resolved_at, resolved_price,
resolution_candles) is left completely unchanged.

Run from the repo root:
    python scripts/rerun_fvg_midpoint_resolution.py
"""
from __future__ import annotations

import logging
import math
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
logger = logging.getLogger("rerun-midpoint")

from api.db import SessionLocal
from api.models import SignalModel
from runner.resolver import (
    MAX_RESOLUTION_CANDLES,
    _last_closed_idx,
    _resolve_midpoint,
    _signal_candle_idx,
)
from strategies.fvg_impulse.data import get_candles

_M15_SECONDS = 15 * 60


def _bars_needed_for(signals: list[SignalModel]) -> int:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    oldest = min(s.candle_time for s in signals)
    if oldest.tzinfo is None:
        oldest = oldest.replace(tzinfo=timezone.utc)
    elapsed = (now - oldest).total_seconds()
    return min(math.ceil(elapsed / _M15_SECONDS) + MAX_RESOLUTION_CANDLES + 10, 500)


def main() -> None:
    db = SessionLocal()
    try:
        # Signals with sl_midpoint — candidates for re-resolution
        all_fvg: list[SignalModel] = (
            db.query(SignalModel)
            .filter(SignalModel.strategy == "fvg-impulse")
            .all()
        )
        targets = [
            s for s in all_fvg
            if isinstance(s.signal_metadata, dict)
            and s.signal_metadata.get("sl_midpoint") is not None
        ]

        if not targets:
            logger.info("No fvg-impulse signals with sl_midpoint found — nothing to do.")
            return

        logger.info(
            "Found %d fvg-impulse signal(s) with sl_midpoint (out of %d total fvg-impulse).",
            len(targets), len(all_fvg),
        )

        already = sum(1 for s in targets if "resolution_midpoint" in (s.signal_metadata or {}))
        logger.info(
            "%d already have resolution_midpoint set (will be recomputed), "
            "%d are fresh (will be computed for first time).",
            already, len(targets) - already,
        )

        confirm = input(
            f"\nThis will recompute resolution_midpoint for {len(targets)} signal(s). Continue? [y/N] "
        ).strip().lower()
        if confirm != "y":
            print("Aborted.")
            sys.exit(0)

        # Group by symbol so we make one candle fetch per symbol
        by_symbol: dict[str, list[SignalModel]] = {}
        for sig in targets:
            by_symbol.setdefault(sig.symbol, []).append(sig)

        total_updated = 0

        for symbol, signals in by_symbol.items():
            count = _bars_needed_for(signals)
            logger.info("Fetching %d bars for %s (%d signal(s))...", count, symbol, len(signals))
            df = get_candles(symbol, count=count)
            if df is None:
                logger.warning("No candle data for %s — skipping %d signal(s).", symbol, len(signals))
                continue

            last_closed = _last_closed_idx(df)
            updated_this_symbol = 0

            for sig in signals:
                start_idx = _signal_candle_idx(df, sig.candle_time)
                if start_idx is None:
                    logger.warning(
                        "  Signal %s (%s %s) candle not found in DataFrame — skipping.",
                        sig.id, sig.symbol, sig.candle_time,
                    )
                    continue

                # Strip stale midpoint resolution so _resolve_midpoint will recompute
                meta = dict(sig.signal_metadata or {})
                meta.pop("resolution_midpoint", None)
                meta.pop("resolution_midpoint_candles", None)
                sig.signal_metadata = meta

                meta_before = dict(sig.signal_metadata)
                _resolve_midpoint(sig, df, start_idx, last_closed)

                new_resolution = (sig.signal_metadata or {}).get("resolution_midpoint")
                if sig.signal_metadata != meta_before:
                    logger.info(
                        "  %s %s %s → midpoint: %s (%s candle(s))",
                        sig.symbol, sig.direction, sig.candle_time.strftime("%Y-%m-%d %H:%M"),
                        new_resolution,
                        (sig.signal_metadata or {}).get("resolution_midpoint_candles", "?"),
                    )
                    updated_this_symbol += 1
                else:
                    logger.info(
                        "  %s %s %s → midpoint still pending (not enough candles yet)",
                        sig.symbol, sig.direction, sig.candle_time.strftime("%Y-%m-%d %H:%M"),
                    )

            if updated_this_symbol:
                db.commit()
                total_updated += updated_this_symbol
                logger.info("  Committed %d update(s) for %s.", updated_this_symbol, symbol)

        logger.info("Done — %d signal(s) updated.", total_updated)
    finally:
        db.close()


if __name__ == "__main__":
    main()
