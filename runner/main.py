"""
runner/main.py
--------------
Scheduler that discovers all strategy scanners under strategies/, runs them
every 15 minutes on candle boundaries, persists new signals to the database,
and sends Discord notifications.

Timing and market-hours logic copied from impulse-notifier/main.py.
Strategy discovery uses pkgutil.iter_modules — no runner changes needed when
a new strategy package is added under strategies/.
"""
from __future__ import annotations

import importlib
import logging
import os
import pkgutil
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

# ---------------------------------------------------------------------------
# Path setup — must happen before any project imports
# ---------------------------------------------------------------------------

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_NOTIFIER_DIR = os.path.join(_ROOT, "impulse-notifier")

for _p in (_ROOT, _NOTIFIER_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

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

from shared.signal import Signal  # noqa: E402
from api.db import SessionLocal, engine, Base  # noqa: E402
from api.models import SignalModel  # noqa: E402  # registers model with Base
from sqlalchemy.orm import Session  # noqa: E402

# Ensure DB tables exist — the runner may start before the API server
Base.metadata.create_all(bind=engine)

try:
    from discord_notifier import send_discord_alert  # impulse-notifier/discord_notifier.py
    _discord_available = True
except ImportError:
    logger.warning("discord_notifier not importable — Discord alerts disabled")
    _discord_available = False

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DISCORD_WEBHOOK_URL: str = os.getenv("DISCORD_WEBHOOK_URL", "")
SCAN_INTERVAL_SECONDS: int = 15 * 60
_STRATEGIES_DIR: str = os.path.join(_ROOT, "strategies")

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
# Market hours — copied verbatim from impulse-notifier/main.py
# ---------------------------------------------------------------------------


def _is_market_open() -> bool:
    """Return True if the forex market is open (Sun 22:00 UTC – Fri 22:00 UTC)."""
    now = datetime.now(timezone.utc)
    day = now.weekday()  # Mon=0 … Sun=6
    hour = now.hour
    if day == 4 and hour >= 22:  # Friday 22:00+
        return False
    if day == 5:  # Saturday
        return False
    if day == 6 and hour < 22:  # Sunday before 22:00 UTC
        return False
    return True


def wait_for_next_candle() -> None:
    """Sleep until the next 15-minute candle boundary + 5-second buffer."""
    now = datetime.now(timezone.utc)
    elapsed = (now.minute % 15) * 60 + now.second
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
            logger.exception("Failed to import %s — skipping", module_path)
            continue
        if not callable(getattr(mod, "scan", None)):
            logger.warning("%s has no scan() function — skipping", module_path)
            continue
        found[name] = mod.scan
        logger.info("Registered strategy: %s", name)
    return found


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _is_duplicate(db: Session, sig: Signal) -> bool:
    """Return True if a signal for (strategy, symbol, candle_time) already exists."""
    return (
        db.query(SignalModel)
        .filter(
            SignalModel.strategy == sig.strategy,
            SignalModel.symbol == sig.symbol,
            SignalModel.candle_time == sig.candle_time,
        )
        .first()
        is not None
    )


def _persist(db: Session, sig: Signal) -> None:
    """Insert a Signal into the DB and commit."""
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
    db.commit()


# ---------------------------------------------------------------------------
# Discord notification
# ---------------------------------------------------------------------------


def _to_discord_dict(sig: Signal) -> dict:
    """Convert a Signal to the dict format expected by discord_notifier.send_discord_alert.

    Base fields are mapped explicitly; strategy-specific extras (e.g. fvg_near_edge)
    live in sig.metadata and are spread in so the FVG embed builder finds them.
    """
    return {
        "symbol": sig.symbol,
        "direction": sig.direction,
        "candle_time": sig.candle_time,
        "entry_price": sig.entry,
        "sl": sig.sl,
        "tp": sig.tp,
        "lot_size": sig.lot_size,
        "risk_pips": sig.risk_pips,
        "spread_pips": sig.spread_pips,
        **sig.metadata,
    }


def _notify_discord(signals: list[Signal]) -> None:
    if not signals:
        return
    if not _discord_available or not DISCORD_WEBHOOK_URL:
        logger.warning("Discord not configured — skipping %d alert(s)", len(signals))
        return
    send_discord_alert(DISCORD_WEBHOOK_URL, [_to_discord_dict(s) for s in signals])


# ---------------------------------------------------------------------------
# Scan cycle
# ---------------------------------------------------------------------------


def run_scan_cycle(strategies: dict[str, object]) -> None:
    """Run one scan cycle: call scan() on every strategy, dedup, persist, notify."""
    if not _is_market_open():
        logger.info("Forex market closed — skipping scan.")
        return

    db = SessionLocal()
    try:
        total_new = 0

        for strategy_name, scan_fn in strategies.items():
            logger.info("[%s] Running scan...", strategy_name)
            try:
                signals: list[Signal] = scan_fn()  # type: ignore[operator]
            except Exception:
                logger.exception("[%s] scan() raised an exception — skipping", strategy_name)
                continue

            new_signals: list[Signal] = []
            for sig in signals:
                if _is_duplicate(db, sig):
                    logger.debug(
                        "[%s] Duplicate skipped: %s %s @ %s",
                        strategy_name,
                        sig.symbol,
                        sig.direction,
                        sig.candle_time,
                    )
                    continue
                _persist(db, sig)
                new_signals.append(sig)

            count = len(new_signals)
            total_new += count

            if count:
                logger.info(
                    "[%s] %d new signal(s): %s",
                    strategy_name,
                    count,
                    ", ".join(f"{s.symbol} {s.direction}" for s in new_signals),
                )
                _notify_discord(new_signals)
            else:
                logger.info("[%s] No new signals this cycle.", strategy_name)

        logger.info(
            "Cycle complete — %d total new signal(s) across %d strategy(ies).",
            total_new,
            len(strategies),
        )
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
        logger.warning("DISCORD_WEBHOOK_URL not set — Discord alerts disabled")

    strategies = discover_strategies()
    if not strategies:
        logger.error(
            "No strategies discovered under %s — check path and __init__.py files",
            _STRATEGIES_DIR,
        )
        sys.exit(1)

    logger.info(
        "Loaded %d strategy(ies): %s",
        len(strategies),
        ", ".join(strategies),
    )

    try:
        # Run immediately on startup, then wait for candle boundaries
        run_scan_cycle(strategies)

        while True:
            wait_for_next_candle()
            try:
                run_scan_cycle(strategies)
            except Exception:
                logger.exception("Scan cycle failed — will retry next candle")
    except KeyboardInterrupt:
        logger.info("Shutting down...")

    logger.info("Goodbye.")


if __name__ == "__main__":
    main()
