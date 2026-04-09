"""
runner/main.py
--------------
Scheduler that discovers all strategy scanners under strategies/, runs them
every 5 minutes on candle boundaries, persists new signals to the database,
and sends Discord notifications.

Timing and market-hours logic copied from impulse-notifier/main.py.
Strategy discovery uses pkgutil.iter_modules -- no runner changes needed when
a new strategy package is added under strategies/.
"""
from __future__ import annotations

import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------------------------------------------------------------------
# Path setup -- must happen before any project imports
# ---------------------------------------------------------------------------

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from dotenv import load_dotenv

load_dotenv(os.path.join(_ROOT, ".env"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("Runner")

# ---------------------------------------------------------------------------
# Project imports (after sys.path is configured)
# ---------------------------------------------------------------------------

from api.db import Base, SessionLocal, engine  # noqa: E402
from api.models import SignalModel  # noqa: E402  # registers model with Base
from runner.helpers import (  # noqa: E402
    discover_strategies,
    is_duplicate,
    is_market_open,
    persist,
    wait_for_next_candle,
)
from runner.notifier import send_signals  # noqa: E402
from runner.resolver import resolve_pending_signals  # noqa: E402
from shared.signal import Signal  # noqa: E402

# Ensure DB tables exist -- the runner may start before the API server
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")

# ---------------------------------------------------------------------------
# Health-check server (port 8080)
# ---------------------------------------------------------------------------


class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *_args: object) -> None:
        pass  # suppress request logs


def _start_health_server() -> None:
    port = int(os.getenv("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    logger.info("Health-check server listening on :%d", port)


# ---------------------------------------------------------------------------
# Discord notification
# ---------------------------------------------------------------------------

def _notify_discord(signals: list[Signal]) -> None:
    if not signals:
        return
    send_signals(signals)


# ---------------------------------------------------------------------------
# Scan cycle
# ---------------------------------------------------------------------------

def run_scan_cycle(strategies: dict[str, object]) -> None:
    """Run one scan cycle: call scan() on every strategy, dedup, persist, notify."""
    if not is_market_open():
        logger.info("Forex market closed -- skipping scan.")
        return

    db = SessionLocal()
    try:
        total_new = 0

        for strategy_name, scan_fn in strategies.items():
            logger.info("[%s] Running scan...", strategy_name)
            try:
                signals: list[Signal] = scan_fn()  # type: ignore[operator]
            except Exception:
                logger.exception("[%s] scan() raised an exception -- skipping", strategy_name)
                continue

            new_signals: list[Signal] = []
            for sig in signals:
                if is_duplicate(db, sig):
                    logger.debug(
                        "[%s] Duplicate skipped: %s %s @ %s",
                        strategy_name, sig.symbol, sig.direction, sig.candle_time,
                    )
                    continue
                persist(db, sig)
                new_signals.append(sig)

            count = len(new_signals)
            total_new += count

            if count:
                logger.info(
                    "[%s] %d new signal(s): %s",
                    strategy_name, count,
                    ", ".join(f"{s.symbol} {s.direction}" for s in new_signals),
                )
                _notify_discord(new_signals)
            else:
                logger.info("[%s] No new signals this cycle.", strategy_name)

        logger.info(
            "Cycle complete -- %d total new signal(s) across %d strategy(ies).",
            total_new, len(strategies),
        )

        resolved = resolve_pending_signals(db)
        if resolved:
            logger.info("Resolution pass: %d signal(s) resolved this cycle.", resolved)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logger.info("=" * 60)
    logger.info("  Forex Dashboard Runner")
    logger.info("=" * 60)

    _start_health_server()

    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not set -- Discord alerts disabled")

    strategies = discover_strategies()
    if not strategies:
        logger.error(
            "No strategies discovered under strategies/ -- check path and __init__.py files",
        )
        sys.exit(1)

    logger.info(
        "Loaded %d strategy(ies): %s",
        len(strategies), ", ".join(strategies),
    )

    try:
        # Run immediately on startup, then wait for candle boundaries
        run_scan_cycle(strategies)

        while True:
            wait_for_next_candle()
            try:
                run_scan_cycle(strategies)
            except Exception:
                logger.exception("Scan cycle failed -- will retry next candle")
    except KeyboardInterrupt:
        logger.info("Shutting down...")

    logger.info("Goodbye.")


if __name__ == "__main__":
    main()
