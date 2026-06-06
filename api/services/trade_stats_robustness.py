"""
api/services/trade_stats_robustness.py
---------------------------------------
Robustness and distribution metrics for backtest-mode trade statistics.
Pure functions — no DB access, no side effects.
"""
from __future__ import annotations

import logging
import math
from statistics import mean, stdev
from typing import Any

from api.models import TradeModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_R_BIN_EDGES: list[float] = [-3.0, -2.0, -1.0, 0.0, 1.0, 2.0, 3.0]
_R_BIN_LABELS: list[str] = [
    "<-3R", "-3 to -2R", "-2 to -1R", "-1 to 0R",
    "0 to 1R", "1 to 2R", "2 to 3R", ">3R",
]
_DECISIVE_OUTCOMES: frozenset[str] = frozenset({"win", "loss"})
_TRIM_PCT: float = 0.05
_ROLLING_PF_WINDOW: int = 20
_CI_Z: float = 1.96
_MIN_N_FOR_STREAK: int = 30


def _bin_index(r: float) -> int:
    """Return the bin index (0-7) for a given R value."""
    for i, edge in enumerate(_R_BIN_EDGES):
        if r < edge:
            return i
    return len(_R_BIN_LABELS) - 1


def compute_r_distribution(closed: list[TradeModel]) -> list[dict[str, Any]]:
    """Compute R distribution across 8 bins, excluding breakeven trades.

    Parameters
    ----------
    closed : list[TradeModel]
        All closed trades (wins, losses, breakevens).

    Returns
    -------
    list of dicts with keys: bucket_label, count, pct.
    """
    r_values = [
        t.rr_achieved
        for t in closed
        if t.outcome in _DECISIVE_OUTCOMES and t.rr_achieved is not None
    ]
    total = len(r_values)
    counts = [0] * len(_R_BIN_LABELS)
    for r in r_values:
        counts[_bin_index(r)] += 1
    return [
        {
            "bucket_label": label,
            "count": counts[i],
            "pct": round(counts[i] / total * 100, 1) if total > 0 else 0.0,
        }
        for i, label in enumerate(_R_BIN_LABELS)
    ]


def _max_drawdown_r(equity_curve: list[dict[str, Any]]) -> float:
    """Compute peak-to-trough drawdown magnitude from equity curve."""
    peak = 0.0
    max_dd = 0.0
    for point in equity_curve:
        cum_r = point.get("cumulative_r", 0.0) or 0.0
        if cum_r > peak:
            peak = cum_r
        dd = peak - cum_r
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _max_losing_streak(closed: list[TradeModel]) -> int:
    """Count the longest consecutive loss streak in trade sequence."""
    streak = 0
    best = 0
    for t in closed:
        if t.outcome == "loss":
            streak += 1
            best = max(best, streak)
        else:
            streak = 0
    return best


def compute_drawdown_stats(
    equity_curve: list[dict[str, Any]],
    closed: list[TradeModel],
) -> dict[str, Any]:
    """Compute max drawdown, losing streak, expected streak, and recovery factor.

    Parameters
    ----------
    equity_curve : list of dicts from build_equity_curve (cumulative_r field required)
    closed : list[TradeModel]
        All closed trades in chronological order.

    Returns
    -------
    dict with keys: max_drawdown_r, max_losing_streak, expected_max_streak, recovery_factor.
    """
    decisive = [t for t in closed if t.outcome in _DECISIVE_OUTCOMES]
    n_decisive = len(decisive)
    n_losses = sum(1 for t in decisive if t.outcome == "loss")
    loss_rate = n_losses / n_decisive if n_decisive > 0 else 0.0

    dd_r = _max_drawdown_r(equity_curve)
    streak = _max_losing_streak(closed)

    expected_streak: float | None = None
    if n_decisive >= _MIN_N_FOR_STREAK and 0.0 < loss_rate < 1.0:
        expected_streak = math.log(n_decisive) / math.log(1.0 / loss_rate)
        expected_streak = round(expected_streak, 2)

    total_r = sum(t.rr_achieved for t in decisive if t.rr_achieved is not None)
    recovery_factor: float | None = None
    if dd_r > 0:
        recovery_factor = round(total_r / dd_r, 3)

    return {
        "max_drawdown_r": round(dd_r, 3),
        "max_losing_streak": streak,
        "expected_max_streak": expected_streak,
        "recovery_factor": recovery_factor,
    }


def compute_expectancy_ci(r_values: list[float]) -> dict[str, Any]:
    """Compute 95% confidence interval around mean R (expectancy).

    Parameters
    ----------
    r_values : list[float]
        R multiples from decisive trades only.

    Returns
    -------
    dict with keys: expectancy_r, expectancy_r_ci_low, expectancy_r_ci_high, edge_significant.
    """
    _null: dict[str, Any] = {
        "expectancy_r": None,
        "expectancy_r_ci_low": None,
        "expectancy_r_ci_high": None,
        "edge_significant": None,
    }
    if len(r_values) < 2:
        return _null
    mean_r = mean(r_values)
    se = stdev(r_values) / math.sqrt(len(r_values))
    ci_low = round(mean_r - _CI_Z * se, 3)
    ci_high = round(mean_r + _CI_Z * se, 3)
    return {
        "expectancy_r": round(mean_r, 3),
        "expectancy_r_ci_low": ci_low,
        "expectancy_r_ci_high": ci_high,
        "edge_significant": ci_low > 0,
    }


def _trim_decisive(decisive: list[TradeModel]) -> list[TradeModel]:
    """Remove top and bottom 5% by rr_achieved."""
    sorted_by_rr = sorted(decisive, key=lambda t: t.rr_achieved)  # type: ignore[arg-type]
    trim = math.floor(len(sorted_by_rr) * _TRIM_PCT)
    if trim == 0:
        return sorted_by_rr
    return sorted_by_rr[trim:-trim]


def compute_edge_robustness(closed: list[TradeModel]) -> dict[str, Any]:
    """Compute profit factor excluding outliers and largest trade concentration.

    Parameters
    ----------
    closed : list[TradeModel]

    Returns
    -------
    dict with keys: profit_factor_ex_outliers, largest_trade_pct_of_pnl.
    """
    decisive = [
        t for t in closed
        if t.outcome in _DECISIVE_OUTCOMES
        and t.rr_achieved is not None
        and t.pnl_usd is not None
    ]

    pf_ex: float | None = None
    if decisive:
        trimmed = _trim_decisive(decisive)
        wins_usd = sum(t.pnl_usd for t in trimmed if t.outcome == "win")  # type: ignore[misc]
        losses_usd = sum(t.pnl_usd for t in trimmed if t.outcome == "loss")  # type: ignore[misc]
        if losses_usd < 0:
            pf_ex = round(wins_usd / abs(losses_usd), 3)

    largest_pct: float | None = None
    if decisive:
        gross_profit = sum(t.pnl_usd for t in decisive if t.outcome == "win")  # type: ignore[misc]
        if gross_profit > 0:
            max_abs = max(abs(t.pnl_usd) for t in decisive)  # type: ignore[arg-type]
            largest_pct = round(max_abs / gross_profit * 100, 1)

    return {
        "profit_factor_ex_outliers": pf_ex,
        "largest_trade_pct_of_pnl": largest_pct,
    }


def compute_rolling_pf(
    closed: list[TradeModel],
    window: int = _ROLLING_PF_WINDOW,
) -> list[dict[str, Any]]:
    """Compute rolling profit factor over a sliding window of decisive trades.

    Parameters
    ----------
    closed : list[TradeModel]
        All closed trades (any order — will be sorted by open_time).
    window : int
        Number of decisive trades per window (default 20).

    Returns
    -------
    list of dicts with keys: index, profit_factor. Returns [] when fewer
    than `window` decisive trades exist.
    """
    decisive = [
        t for t in closed
        if t.outcome in _DECISIVE_OUTCOMES and t.pnl_usd is not None
    ]
    decisive.sort(key=lambda t: t.open_time)
    if len(decisive) < window:
        return []
    result: list[dict[str, Any]] = []
    for i in range(window, len(decisive) + 1):
        batch = decisive[i - window:i]
        gross_win = sum(t.pnl_usd for t in batch if t.outcome == "win")  # type: ignore[misc]
        gross_loss = abs(sum(t.pnl_usd for t in batch if t.outcome == "loss"))  # type: ignore[misc]
        pf: float | None = round(gross_win / gross_loss, 3) if gross_loss > 0 else None
        result.append({"index": i - 1, "profit_factor": pf})
    return result
