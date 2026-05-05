"""
scripts/backfill_signals.py
---------------------------
Backfill missed signals by replaying each strategy scanner against historical
candle data — one M15 candle at a time, strictly as-of each candle's close.

Zero lookahead bias guarantees
-------------------------------
1. Each scan receives only candles.iloc[:i+1] — future rows are not in the slice.
2. datetime.now() is patched to candle_time + interval + 30s so the scanner's
   _find_last_closed_index() selects exactly the target candle.
3. _alerted_candles is cleared before every iteration.
4. Signals are only emitted for candles in [start, end); the fetch window extends
   80 bars before start so FVG state warms up before the first emitted signal.
5. Every emitted signal is asserted: candle_time == slice[-1] and candle_time < fake_now.
   With --strict these assertions abort the run; without --strict they log errors.

No Discord notifications are sent.

Usage:
    python scripts/backfill_signals.py --from 2026-04-15 --to 2026-04-30
    python scripts/backfill_signals.py --from 2026-04-15 --dry-run
    python scripts/backfill_signals.py --from 2026-04-15 --strict --run-id abc123
"""
from __future__ import annotations

import argparse
import importlib
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("backfill")

from api.db import Base, SessionLocal, engine  # noqa: E402
from runner.helpers import is_duplicate, persist  # noqa: E402
from shared.signal import Signal  # noqa: E402

Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WARMUP_BARS: int = 80  # bars prepended before start to warm up FVG state

# Each entry: (slug, module_path, interval_minutes, candle_count_per_symbol)
_STRATEGIES: list[tuple[str, str, int, int]] = [
    ("fvg-impulse",    "strategies.fvg_impulse.scanner",    15, 500),
    ("fvg-impulse-5m", "strategies.fvg_impulse_5m.scanner", 5,  1500),
    ("nova-candle",    "strategies.nova_candle.scanner",     15, 500),
]


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

@dataclass
class BackfillReport:
    run_id: str
    dry_run: bool
    inserted: int = 0
    skipped: int = 0
    violations: int = 0
    per_strategy: dict[str, dict[str, int]] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Bias-free helpers
# ---------------------------------------------------------------------------

def fake_now_for_index(candles: Any, idx: int, interval_minutes: int) -> datetime:
    """Return a fake 'now' that makes idx the last closed candle.

    Placing fake_now interval+30s after the candle puts current_boundary at
    candle_time+interval, so _find_last_closed_index returns idx.
    """
    candle_time = candles.index[idx].to_pydatetime()
    return candle_time + timedelta(minutes=interval_minutes, seconds=30)


def slice_as_of(candles: Any, idx: int) -> Any:
    """Return candles[:idx+1] — the strict as-of slice for bar idx."""
    return candles.iloc[: idx + 1]


def emit_indices(candles: Any, start: datetime, end: datetime) -> list[int]:
    """Return indices whose candle_time is in [start, end) and index >= 2."""
    result = []
    for i, ts in enumerate(candles.index):
        ct = ts.to_pydatetime()
        if ct >= start and ct < end and i >= 2:
            result.append(i)
    return result


def _check_signal_invariants(
    sig: Signal,
    as_of_candle_time: datetime,
    fake_now: datetime,
    strict: bool,
) -> bool:
    """Assert no lookahead bias. Returns True if clean, False on violation."""
    ok = True
    if sig.candle_time != as_of_candle_time:
        msg = (
            f"INVARIANT VIOLATION: signal.candle_time {sig.candle_time} "
            f"!= as_of {as_of_candle_time}"
        )
        if strict:
            raise RuntimeError(msg)
        logger.error(msg)
        ok = False
    if sig.candle_time >= fake_now:
        msg = (
            f"LOOKAHEAD BIAS: signal.candle_time {sig.candle_time} "
            f">= fake_now {fake_now}"
        )
        if strict:
            raise RuntimeError(msg)
        logger.error(msg)
        ok = False
    return ok


# ---------------------------------------------------------------------------
# Per-strategy replay
# ---------------------------------------------------------------------------

def _replay_fvg(
    scanner_mod: Any,
    slug: str,
    symbol: str,
    candles: Any,
    indices: list[int],
    interval_minutes: int,
    run_id: str,
    strict: bool,
) -> tuple[list[Signal], int]:
    """Replay FVG scanner (fvg-impulse or fvg-impulse-5m) for each index.

    Returns (signals, violation_count).
    """
    results: list[Signal] = []
    violations = 0

    for idx in indices:
        as_of_candle_time = candles.index[idx].to_pydatetime()
        fake_now = fake_now_for_index(candles, idx, interval_minutes)
        sliced = slice_as_of(candles, idx)

        scanner_mod._alerted_candles.clear()
        with patch(f"{scanner_mod.__name__}.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            raw_signals = scanner_mod.scan_symbol(sliced, symbol)

        for raw in raw_signals:
            sig = scanner_mod._to_signal(raw)
            sig.metadata["backfill"] = True
            sig.metadata["backfill_run_id"] = run_id
            sig.metadata["as_of_time"] = fake_now.isoformat()

            if not _check_signal_invariants(sig, as_of_candle_time, fake_now, strict):
                violations += 1
                continue
            results.append(sig)

        scanner_mod._alerted_candles.clear()

    return results, violations


def _replay_nova(
    scanner_mod: Any,
    symbol: str,
    candles: Any,
    indices: list[int],
    interval_minutes: int,
    run_id: str,
    strict: bool,
) -> tuple[list[Signal], int]:
    """Replay nova-candle scanner for each index.

    Returns (signals, violation_count).
    """
    from strategies.nova_candle.calculations import calculate_trade_params  # noqa: PLC0415

    results: list[Signal] = []
    violations = 0

    for idx in indices:
        as_of_candle_time = candles.index[idx].to_pydatetime()
        fake_now = fake_now_for_index(candles, idx, interval_minutes)
        sliced = slice_as_of(candles, idx)

        scanner_mod._alerted_candles.clear()
        with patch(f"{scanner_mod.__name__}.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
            result = scanner_mod.find_nova_candle(sliced, symbol)

        if result is None:
            scanner_mod._alerted_candles.clear()
            continue

        result["symbol"] = symbol
        trade_params = calculate_trade_params(result, sliced, idx)
        if trade_params is None:
            scanner_mod._alerted_candles.clear()
            continue

        result.update(trade_params)
        sig = scanner_mod._to_signal(result)
        sig.metadata["backfill"] = True
        sig.metadata["backfill_run_id"] = run_id
        sig.metadata["as_of_time"] = fake_now.isoformat()

        if not _check_signal_invariants(sig, as_of_candle_time, fake_now, strict):
            violations += 1
            scanner_mod._alerted_candles.clear()
            continue

        results.append(sig)
        scanner_mod._alerted_candles.clear()

    return results, violations


# ---------------------------------------------------------------------------
# Main backfill loop
# ---------------------------------------------------------------------------

def backfill(
    start: datetime,
    end: datetime,
    dry_run: bool = False,
    strict: bool = False,
    run_id: str | None = None,
    warmup_bars: int = WARMUP_BARS,
    strategies: list[str] | None = None,
    symbols: list[str] | None = None,
) -> BackfillReport:
    """Run the full backfill from start to end.

    Parameters
    ----------
    strategies : list of slug strings to run, e.g. ["fvg-impulse"].
                 None means all strategies in _STRATEGIES.
    symbols    : override the symbol list for every strategy run.
                 None means use each strategy's env-var / DEFAULT_PAIRS.
    """
    run_id = run_id or str(uuid.uuid4())
    report = BackfillReport(run_id=run_id, dry_run=dry_run)

    active = [
        (slug, mod, iv, cc) for slug, mod, iv, cc in _STRATEGIES
        if strategies is None or slug in strategies
    ]
    if not active:
        logger.error("No matching strategies for filter %s. Valid: %s",
                     strategies, [s for s, *_ in _STRATEGIES])
        return report

    logger.info(
        "Backfill start — run_id=%s  window=%s → %s  strategies=%s  dry_run=%s  strict=%s",
        run_id, start, end, [s for s, *_ in active], dry_run, strict,
    )

    db = SessionLocal()
    try:
        for slug, module_path, interval_minutes, candle_count in active:
            _run_strategy(
                db, slug, module_path, interval_minutes, candle_count,
                start, end, dry_run, strict, run_id, warmup_bars, report,
                symbols_override=symbols,
            )
    finally:
        db.close()

    logger.info(
        "Backfill complete — run_id=%s  inserted=%d  skipped=%d  violations=%d",
        run_id, report.inserted, report.skipped, report.violations,
    )
    return report


def _run_strategy(
    db: Any,
    slug: str,
    module_path: str,
    interval_minutes: int,
    candle_count: int,
    start: datetime,
    end: datetime,
    dry_run: bool,
    strict: bool,
    run_id: str,
    warmup_bars: int,
    report: BackfillReport,
    symbols_override: list[str] | None = None,
) -> None:
    """Run backfill for one strategy across all its symbols."""
    logger.info("=" * 60)
    logger.info("Strategy: %s  (interval=%dm)", slug, interval_minutes)

    mod = importlib.import_module(module_path)
    if symbols_override:
        symbols = symbols_override
    else:
        env_key = slug.upper().replace("-", "_") + "_PAIRS"
        pairs_str = os.getenv(env_key, mod.DEFAULT_PAIRS)
        symbols = [p.strip() for p in pairs_str.split(",") if p.strip()]

    stat: dict[str, int] = {"inserted": 0, "skipped": 0, "violations": 0}

    for symbol in symbols:
        _run_symbol(
            db, mod, slug, symbol, interval_minutes, candle_count,
            start, end, dry_run, strict, run_id, warmup_bars, stat,
        )

    report.per_strategy[slug] = stat
    report.inserted += stat["inserted"]
    report.skipped += stat["skipped"]
    report.violations += stat["violations"]
    logger.info(
        "[%s] Done: inserted=%d skipped=%d violations=%d",
        slug, stat["inserted"], stat["skipped"], stat["violations"],
    )


def _run_symbol(
    db: Any,
    mod: Any,
    slug: str,
    symbol: str,
    interval_minutes: int,
    candle_count: int,
    start: datetime,
    end: datetime,
    dry_run: bool,
    strict: bool,
    run_id: str,
    warmup_bars: int,
    stat: dict[str, int],
) -> None:
    """Fetch candles and replay one symbol for one strategy."""
    # tvDatafeed returns the most recent N bars ending at roughly now.
    # To reach back to (start - warmup), we need bars from now all the way back.
    from datetime import datetime as _dt  # noqa: PLC0415
    now = _dt.now(timezone.utc)
    bars_from_now_to_start = int((now - start).total_seconds() / (interval_minutes * 60)) + 1
    fetch_count = bars_from_now_to_start + warmup_bars + 50

    logger.info("[%s] Fetching %d bars for %s...", slug, fetch_count, symbol)

    if slug == "nova-candle":
        from shared.market_data import get_candles as _gc  # noqa: PLC0415
        from tvDatafeed import Interval  # noqa: PLC0415
        candles = _gc(symbol, Interval.in_15_minute, fetch_count)
    else:
        candles = mod.get_candles(symbol, fetch_count)

    if candles is None:
        logger.warning("[%s] No candles for %s — skipping", slug, symbol)
        return

    if candles.index.tz is None:
        logger.warning("[%s] %s: candles have no timezone — skipping", slug, symbol)
        return

    indices = emit_indices(candles, start, end)
    if not indices:
        logger.info("[%s] %s: no candles in emit window", slug, symbol)
        return

    logger.info("[%s] %s: scanning %d candle(s) in window", slug, symbol, len(indices))

    if slug == "nova-candle":
        signals, viols = _replay_nova(
            mod, symbol, candles, indices, interval_minutes, run_id, strict,
        )
    else:
        signals, viols = _replay_fvg(
            mod, slug, symbol, candles, indices, interval_minutes, run_id, strict,
        )

    stat["violations"] += viols

    for sig in signals:
        if is_duplicate(db, sig):
            logger.debug("[%s] Duplicate: %s %s @ %s", slug, sig.symbol, sig.direction, sig.candle_time)
            stat["skipped"] += 1
            continue

        if dry_run:
            logger.info(
                "[DRY RUN] %s %s %s @ %s entry=%.5f sl=%.5f tp=%.5f",
                sig.strategy, sig.symbol, sig.direction,
                sig.candle_time.strftime("%Y-%m-%dT%H:%M"),
                sig.entry, sig.sl, sig.tp,
            )
            stat["inserted"] += 1
        else:
            if persist(db, sig):
                logger.info(
                    "Inserted: %s %s %s @ %s",
                    sig.strategy, sig.symbol, sig.direction, sig.candle_time,
                )
                stat["inserted"] += 1
                db.commit()
            else:
                stat["skipped"] += 1


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill missed signals into the DB with zero lookahead bias.",
    )
    parser.add_argument(
        "--from", dest="start", default="2026-04-18",
        help="Start date (UTC, inclusive) YYYY-MM-DD. Default: 2026-04-18",
    )
    parser.add_argument(
        "--to", dest="end", default=None,
        help="End date (UTC, exclusive) YYYY-MM-DD. Default: now",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be inserted without writing to the DB.",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Abort on any lookahead-bias invariant violation (exit 2).",
    )
    parser.add_argument(
        "--run-id", dest="run_id", default=None,
        help="Explicit UUID for this run (for idempotent reruns). Default: auto-generated.",
    )
    parser.add_argument(
        "--warmup-bars", dest="warmup_bars", type=int, default=WARMUP_BARS,
        help=f"Bars of history prepended before start for FVG state warm-up. Default: {WARMUP_BARS}",
    )
    parser.add_argument(
        "--strategy", dest="strategies", default=None,
        help="Comma-separated strategy slugs to run, e.g. fvg-impulse,nova-candle. Default: all.",
    )
    parser.add_argument(
        "--symbols", dest="symbols", default=None,
        help="Comma-separated symbol override for all strategies, e.g. EURUSD,GBPUSD.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    start_dt = datetime.strptime(args.start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = (
        datetime.strptime(args.end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if args.end
        else datetime.now(timezone.utc)
    )

    strategies_filter = (
        [s.strip() for s in args.strategies.split(",") if s.strip()]
        if args.strategies else None
    )
    symbols_filter = (
        [s.strip() for s in args.symbols.split(",") if s.strip()]
        if args.symbols else None
    )

    try:
        report = backfill(
            start_dt, end_dt,
            dry_run=args.dry_run,
            strict=args.strict,
            run_id=args.run_id,
            warmup_bars=args.warmup_bars,
            strategies=strategies_filter,
            symbols=symbols_filter,
        )
    except RuntimeError as exc:
        logger.error("Backfill aborted: %s", exc)
        sys.exit(2)

    if report.violations > 0:
        logger.error("Run completed with %d invariant violations.", report.violations)
        sys.exit(1)
