"""
FVG Identifier - Virgin FVG Wick-Test Scanner & Discord Notifier

Fetches forex M15 candles from TradingView every 15 minutes,
scans for virgin FVG wick-test rejections, and sends alerts to Discord.

Required .env variables:
    DISCORD_WEBHOOK_URL             -- Discord webhook URL

Optional .env variables:
    SCAN_PAIRS          -- comma-separated pairs (default: 7 pairs)
"""
from __future__ import annotations

import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler


def _is_market_open() -> bool:
    """Check if the forex market is currently open (Sun 22:00 UTC - Fri 22:00 UTC)."""
    now = datetime.now(timezone.utc)
    day = now.weekday()  # Mon=0 ... Sun=6
    hour = now.hour
    if day == 4 and hour >= 22:  # Friday 22:00+
        return False
    if day == 5:  # Saturday
        return False
    if day == 6 and hour < 22:  # Sunday before 22:00
        return False
    return True


_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(_SCRIPT_DIR, ".env"))

from scanner import scan_all_symbols
from discord_notifier import send_discord_alert

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

DEFAULT_PAIRS = "EURUSD,AUDUSD,NZDUSD,USDJPY,USDCHF,USDCAD,GBPUSD"
SCAN_PAIRS = [
    p.strip()
    for p in os.getenv("SCAN_PAIRS", DEFAULT_PAIRS).split(",")
    if p.strip()
]

SCAN_INTERVAL_SECONDS = 15 * 60

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_FILE = os.path.join(_SCRIPT_DIR, "fvg_scanner.log")

_handlers: list[logging.Handler] = [logging.StreamHandler()]
try:
    _handlers.append(logging.FileHandler(_LOG_FILE))
except OSError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=_handlers,
)
logger = logging.getLogger("FVGScanner")


# ---------------------------------------------------------------------------
# Health check server
# ---------------------------------------------------------------------------

class _HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *_args):
        pass


def _start_health_server() -> None:
    port = int(os.getenv("PORT", "8080"))
    server = HTTPServer(("0.0.0.0", port), _HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info("Health-check server listening on :%d", port)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_scan() -> None:
    """Run a single scan cycle."""
    if not _is_market_open():
        logger.info("Forex market closed, skipping scan.")
        return
    logger.info("Scanning %d pairs: %s", len(SCAN_PAIRS), ", ".join(SCAN_PAIRS))

    signals = scan_all_symbols(SCAN_PAIRS)

    if signals:
        logger.info("Found %d FVG signal(s)!", len(signals))
        for s in signals:
            logger.info("  %s %s @ %s (near=%.5f far=%.5f width=%.1fpip)",
                        s["symbol"], s["direction"], s["candle_time"],
                        s["fvg_near_edge"], s["fvg_far_edge"], s["fvg_width_pips"])
        send_discord_alert(DISCORD_WEBHOOK_URL, signals)
    else:
        logger.info("No FVG signals found this cycle.")


def wait_for_next_candle() -> None:
    """Sleep until the next 15-minute candle boundary + 5 seconds buffer."""
    now = datetime.now(timezone.utc)
    elapsed = (now.minute % 15) * 60 + now.second
    seconds_to_wait = SCAN_INTERVAL_SECONDS - elapsed + 5
    if seconds_to_wait <= 5:
        seconds_to_wait += SCAN_INTERVAL_SECONDS
    next_time = datetime.fromtimestamp(now.timestamp() + seconds_to_wait, tz=timezone.utc)
    logger.info("Next scan at %s (in %d seconds)", next_time.strftime("%H:%M:%S UTC"), seconds_to_wait)
    time.sleep(seconds_to_wait)


def main() -> None:
    logger.info("=" * 60)
    logger.info("  FVG Identifier -- Virgin FVG Wick-Test Scanner")
    logger.info("=" * 60)

    _start_health_server()

    if not DISCORD_WEBHOOK_URL:
        logger.warning("DISCORD_WEBHOOK_URL not set -- alerts will be logged only")

    logger.info("Scanning %d pairs via TradingView (PEPPERSTONE)", len(SCAN_PAIRS))

    try:
        run_scan()

        while True:
            wait_for_next_candle()
            try:
                run_scan()
            except Exception:
                logger.exception("Scan cycle failed")
    except KeyboardInterrupt:
        logger.info("Shutting down...")

    logger.info("Goodbye.")


if __name__ == "__main__":
    main()
