"""
api/services/trade_stats_live.py
----------------------------------
Live-account statistics: drawdown metrics, rolling expectancy, and TP capture.
Pure functions — no DB access, no side effects.
"""
from __future__ import annotations

import logging
from datetime import datetime
from statistics import mean
from typing import Any

from api.models import TradeModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_ROLLING_WINDOW: int = 30
_WIN_OUTCOME: str = "win"


def compute_drawdown(equity_curve: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute live-account drawdown metrics from an equity curve.

    Parameters
    ----------
    equity_curve : list of dicts
        Each point must have ``cumulative_r`` (float) and
        ``cumulative_pnl_usd`` (float) — produced by ``build_equity_curve``.

    Returns
    -------
    dict with keys: max_drawdown_usd, max_drawdown_r, current_drawdown_usd,
    current_drawdown_pct, drawdown_trade_count, recovery_factor.
    """
    _empty: dict[str, Any] = {
        "max_drawdown_usd": 0.0,
        "max_drawdown_r": 0.0,
        "current_drawdown_usd": 0.0,
        "current_drawdown_pct": 0.0,
        "drawdown_trade_count": 0,
        "recovery_factor": None,
    }
    if not equity_curve:
        return _empty

    peak_usd = 0.0
    peak_r = 0.0
    max_dd_usd = 0.0
    max_dd_r = 0.0

    for point in equity_curve:
        cum_usd = point.get("cumulative_pnl_usd", 0.0) or 0.0
        cum_r = point.get("cumulative_r", 0.0) or 0.0

        if cum_usd > peak_usd:
            peak_usd = cum_usd
        if peak_usd > 0:
            dd_usd = peak_usd - cum_usd
            if dd_usd > max_dd_usd:
                max_dd_usd = dd_usd

        if cum_r > peak_r:
            peak_r = cum_r
        if peak_r > 0:
            dd_r = peak_r - cum_r
            if dd_r > max_dd_r:
                max_dd_r = dd_r

    last_usd = equity_curve[-1].get("cumulative_pnl_usd", 0.0) or 0.0
    current_dd_usd = max(peak_usd - last_usd, 0.0)
    current_dd_pct = (current_dd_usd / peak_usd * 100) if peak_usd > 0 else 0.0

    drawdown_trade_count = _count_underwater_streak(equity_curve, peak_usd)
    recovery_factor = _calc_recovery_factor(last_usd, max_dd_usd)

    return {
        "max_drawdown_usd": round(max_dd_usd, 2),
        "max_drawdown_r": round(max_dd_r, 3),
        "current_drawdown_usd": round(current_dd_usd, 2),
        "current_drawdown_pct": round(current_dd_pct, 2),
        "drawdown_trade_count": drawdown_trade_count,
        "recovery_factor": recovery_factor,
    }


def _count_underwater_streak(
    equity_curve: list[dict[str, Any]], peak_usd: float,
) -> int:
    """Count consecutive trailing points where cumulative_pnl_usd < peak_usd."""
    if peak_usd <= 0:
        return 0
    count = 0
    for point in reversed(equity_curve):
        cum_usd = point.get("cumulative_pnl_usd", 0.0) or 0.0
        if cum_usd < peak_usd:
            count += 1
        else:
            break
    return count


def _calc_recovery_factor(total_pnl_usd: float, max_dd_usd: float) -> float | None:
    """Return total_pnl_usd / max_dd_usd, or None when undefined."""
    if max_dd_usd == 0 or total_pnl_usd <= 0:
        return None
    return round(total_pnl_usd / max_dd_usd, 3)


def compute_rolling_expectancy(
    closed: list[TradeModel],
    window: int = DEFAULT_ROLLING_WINDOW,
) -> list[dict[str, Any]]:
    """Return rolling expectancy over a sliding window of trades with rr_achieved.

    Parameters
    ----------
    closed : list[TradeModel]
        All closed trades (any order — sorted internally by open_time).
    window : int
        Sliding-window size (default 30). Returns [] when fewer than
        ``window`` qualifying trades exist.

    Returns
    -------
    list of dicts with keys: index, close_time, rolling_expectancy_r.
    """
    qualifying = sorted(
        (t for t in closed if t.rr_achieved is not None),
        key=lambda t: t.open_time,
    )
    if len(qualifying) < window:
        return []

    result: list[dict[str, Any]] = []
    for i in range(len(qualifying) - window + 1):
        batch = qualifying[i : i + window]
        rr_values = [t.rr_achieved for t in batch]  # type: ignore[misc]
        expectancy = round(mean(rr_values), 3)
        last_trade = batch[-1]
        result.append({
            "index": i + window - 1,
            "close_time": last_trade.open_time,
            "rolling_expectancy_r": expectancy,
        })
    return result


def compute_tp_capture(closed: list[TradeModel]) -> dict[str, Any]:
    """Compute average TP capture percentage for winning trades.

    Measures how far into the TP target the exit was — e.g. 0.75 means
    the trade captured 75% of the distance from entry to TP.
    Values > 1.0 are valid (exit beyond TP).

    Parameters
    ----------
    closed : list[TradeModel]
        All closed trades; only winning trades are included.

    Returns
    -------
    dict with keys: avg_tp_capture_pct (float | None), tp_capture_sample_size (int).
    """
    ratios: list[float] = []
    for trade in closed:
        if trade.outcome != _WIN_OUTCOME:
            continue
        ratio = _tp_capture_ratio(trade)
        if ratio is not None:
            ratios.append(ratio)

    avg: float | None = None
    if ratios:
        avg = round(mean(ratios) * 100, 1)

    return {"avg_tp_capture_pct": avg, "tp_capture_sample_size": len(ratios)}


def _tp_capture_ratio(trade: TradeModel) -> float | None:
    """Compute the TP capture ratio for a single winning trade.

    Returns None when tp_price is missing or equals entry (div-by-zero guard).
    """
    if trade.tp_price is None or trade.exit_price is None:
        return None

    entry = trade.entry_price
    tp = trade.tp_price
    exit_price = trade.exit_price

    if trade.direction == "BUY":
        denominator = tp - entry
        numerator = exit_price - entry
    else:
        denominator = entry - tp
        numerator = entry - exit_price

    if denominator == 0:
        return None

    return numerator / denominator
