"""
api/services/trade_stats_extended.py
------------------------------------
Extended pure functions for trade statistics: equity curve, daily summary,
edge metrics, and dimensional breakdowns (day-of-week, session, assessment).

Split from trade_stats.py to keep each module under the 200-line limit.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from typing import Any, Callable

from api.models import TradeModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Session hour boundaries (UTC)
# ---------------------------------------------------------------------------

# NOTE: These boundaries differ from _SESSION_RANGES in analytics/params/temporal.py.
# That module uses finer-grained sessions (asian 0-7, london 7-12, ny_overlap 12-16,
# ny_late 16-21, close 21-24) for per-signal analytics classification.
# These boundaries are coarser and used only for trade-level journal aggregation.
# Neither is authoritative over the other — they serve different purposes.
# Reconcile both if a single session taxonomy is ever required project-wide.
_SESSIONS: list[tuple[str, int, int]] = [
    ("asian", 0, 8),
    ("london", 8, 13),
    ("overlap", 13, 17),
    ("new_york", 17, 22),
    ("off_hours", 22, 24),
]

_DAY_NAMES: dict[int, str] = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday",
    3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday",
}


def _classify_session(hour: int) -> str:
    """Return the session name for a given UTC hour."""
    for name, start, end in _SESSIONS:
        if start <= hour < end:
            return name
    return "off_hours"


def build_equity_curve(closed: list[TradeModel]) -> list[dict[str, Any]]:
    """Build cumulative P&L curve from closed trades ordered by open_time.

    Returns a list of dicts with per-trade P&L and running cumulative totals.
    """
    sorted_trades = sorted(
        closed, key=lambda t: t.open_time,
    )
    cum_usd = 0.0
    cum_pips = 0.0
    result: list[dict[str, Any]] = []
    for t in sorted_trades:
        pnl_usd = t.pnl_usd or 0.0
        pnl_pips = t.pnl_pips or 0.0
        cum_usd += pnl_usd
        cum_pips += pnl_pips
        ct = t.open_time
        result.append({
            "date": ct.date().isoformat() if ct else None,
            "close_time": ct.isoformat() if ct else None,
            "pnl_usd": round(pnl_usd, 2),
            "pnl_pips": round(pnl_pips, 1),
            "cumulative_pnl_usd": round(cum_usd, 2),
            "cumulative_pnl_pips": round(cum_pips, 1),
            "trade_count": 1,
            "outcome": t.outcome,
        })
    return result


def build_daily_summary(closed: list[TradeModel]) -> list[dict[str, Any]]:
    """Aggregate closed trades by open_time date for the calendar."""
    buckets: dict[date, dict[str, Any]] = {}
    for t in closed:
        ct = t.open_time
        if ct is None:
            continue
        d = ct.date()
        if d not in buckets:
            buckets[d] = {
                "date": d.isoformat(),
                "trades": 0, "wins": 0, "losses": 0,
                "breakevens": 0, "pnl_usd": 0.0, "pnl_pips": 0.0,
                "compliant": 0, "mistakes": 0,
            }
        buckets[d]["trades"] += 1
        if t.outcome == "win":
            buckets[d]["wins"] += 1
        elif t.outcome == "loss":
            buckets[d]["losses"] += 1
        elif t.outcome == "breakeven":
            buckets[d]["breakevens"] += 1
        buckets[d]["pnl_usd"] += t.pnl_usd or 0.0
        buckets[d]["pnl_pips"] += t.pnl_pips or 0.0
        if t.rule_followed is True:
            buckets[d]["compliant"] += 1
        elif t.rule_followed is False:
            buckets[d]["mistakes"] += 1
    for v in buckets.values():
        v["pnl_usd"] = round(v["pnl_usd"], 2)
        v["pnl_pips"] = round(v["pnl_pips"], 1)
    return sorted(buckets.values(), key=lambda x: x["date"])


def calculate_edge_metrics(closed: list[TradeModel]) -> dict[str, Any]:
    """Compute avg win/loss, expectancy, and consistency ratio."""
    wins = [t for t in closed if t.outcome == "win"]
    losses = [t for t in closed if t.outcome == "loss"]
    win_pips = [t.pnl_pips for t in wins if t.pnl_pips is not None]
    loss_pips = [t.pnl_pips for t in losses if t.pnl_pips is not None]
    win_usd = [t.pnl_usd for t in wins if t.pnl_usd is not None]
    loss_usd = [t.pnl_usd for t in losses if t.pnl_usd is not None]

    avg_win_pips = round(sum(win_pips) / len(win_pips), 1) if win_pips else None
    avg_loss_pips = round(abs(sum(loss_pips) / len(loss_pips)), 1) if loss_pips else None
    avg_win_usd = round(sum(win_usd) / len(win_usd), 2) if win_usd else None
    avg_loss_usd = round(abs(sum(loss_usd) / len(loss_usd)), 2) if loss_usd else None

    total_decisive = len(wins) + len(losses)
    expectancy_usd = _calc_expectancy(avg_win_usd, avg_loss_usd, wins, losses, total_decisive)
    expectancy_pips = _calc_expectancy(avg_win_pips, avg_loss_pips, wins, losses, total_decisive)
    consistency = _calc_consistency(closed)

    return {
        "avg_win_pips": avg_win_pips,
        "avg_loss_pips": avg_loss_pips,
        "avg_win_usd": avg_win_usd,
        "avg_loss_usd": avg_loss_usd,
        "expectancy_usd": expectancy_usd,
        "expectancy_pips": expectancy_pips,
        "consistency_ratio": consistency,
    }


def _calc_expectancy(
    avg_win: float | None,
    avg_loss: float | None,
    wins: list[TradeModel],
    losses: list[TradeModel],
    total: int,
) -> float | None:
    """(win_rate * avg_win) - (loss_rate * avg_loss)."""
    if avg_win is None or avg_loss is None or total == 0:
        return None
    wr = len(wins) / total
    lr = len(losses) / total
    return round(wr * avg_win - lr * avg_loss, 2)


def _calc_consistency(closed: list[TradeModel]) -> float | None:
    """Percentage of ISO weeks with net positive P&L."""
    weekly_pnl: dict[tuple[int, int], float] = defaultdict(float)
    for t in closed:
        ct = t.open_time
        if ct is None or t.pnl_usd is None:
            continue
        iso = ct.isocalendar()
        weekly_pnl[(iso[0], iso[1])] += t.pnl_usd
    if not weekly_pnl:
        return None
    positive = sum(1 for v in weekly_pnl.values() if v > 0)
    return round(positive / len(weekly_pnl) * 100, 1)


def aggregate_by_day_of_week(closed: list[TradeModel]) -> dict[str, dict]:
    """Group closed trades by day-of-week (from open_time)."""
    def key_fn(t: TradeModel) -> int | None:
        return t.open_time.weekday() if t.open_time else None
    raw = _aggregate_dimension(closed, key_fn)
    return {str(k): {**v, "name": _DAY_NAMES[k]} for k, v in sorted(raw.items())}


def aggregate_by_session(closed: list[TradeModel]) -> dict[str, dict]:
    """Group closed trades by trading session (from open_time UTC hour)."""
    def key_fn(t: TradeModel) -> str | None:
        return _classify_session(t.open_time.hour) if t.open_time else None
    raw = _aggregate_dimension(closed, key_fn)
    return {k: {**v, "name": k} for k, v in raw.items()}


def aggregate_by_assessment(
    closed: list[TradeModel], field: str,
) -> dict[str, dict]:
    """Group by an integer assessment field (confidence or rating)."""
    def key_fn(t: TradeModel) -> int | None:
        return getattr(t, field, None)
    raw = _aggregate_dimension(closed, key_fn)
    return {str(k): {**v, "name": str(k)} for k, v in sorted(raw.items())}


_RULE_BUCKET: dict[bool | None, str] = {
    True: "compliant", False: "mistake", None: "unreviewed",
}

_CRITERIA_BUCKET: dict[bool | None, str] = {
    True: "met", False: "not_met",
}


def aggregate_by_rule_compliance(closed: list[TradeModel]) -> dict[str, dict]:
    """Group closed trades by rule_followed value.

    Buckets: 'compliant' (True), 'mistake' (False), 'unreviewed' (None).
    All trades are included — rule_followed=None maps to 'unreviewed'.
    """
    def key_fn(t: TradeModel) -> str:
        return _RULE_BUCKET[t.rule_followed]

    raw = _aggregate_dimension(closed, key_fn)
    return {k: {**v, "name": k} for k, v in raw.items()}


def aggregate_by_criteria_met(closed: list[TradeModel]) -> dict[str, dict]:
    """Group closed trades by criteria_met_at_entry value.

    Buckets: 'met' (True), 'not_met' (False). Trades with None are excluded —
    criteria_met_at_entry is only recorded on backtest trades.
    """
    def key_fn(t: TradeModel) -> str | None:
        v = t.criteria_met_at_entry
        if v is None:
            return None
        return _CRITERIA_BUCKET[v]

    raw = _aggregate_dimension(closed, key_fn)
    return {k: {**v, "name": k} for k, v in raw.items()}


def aggregate_be_outcome(closed: list[TradeModel]) -> dict[str, int]:
    """Count BE trades by be_outcome value.

    Only trades with outcome='breakeven' are included.
    Returns: {'prevented_loss': N, 'missed_tp': N, 'unreviewed': N}
    """
    be_trades = [t for t in closed if t.outcome == "breakeven"]
    result: dict[str, int] = {"prevented_loss": 0, "missed_tp": 0, "unreviewed": 0}
    for t in be_trades:
        if t.be_outcome == "prevented_loss":
            result["prevented_loss"] += 1
        elif t.be_outcome == "missed_tp":
            result["missed_tp"] += 1
        else:
            result["unreviewed"] += 1
    return result


def _aggregate_dimension(
    closed: list[TradeModel],
    key_fn: Callable[[TradeModel], int | str | None],
) -> dict[Any, dict[str, Any]]:
    """Generic dimension aggregation: group trades by key_fn result."""
    buckets: dict[Any, dict[str, Any]] = {}
    for t in closed:
        key = key_fn(t)
        if key is None:
            continue
        if key not in buckets:
            buckets[key] = {
                "total": 0, "wins": 0, "losses": 0,
                "win_rate": None, "total_pnl_pips": 0.0,
                "total_pnl_usd": 0.0, "avg_pnl_usd": None,
                "avg_rr": None, "_rr": [],
            }
        b = buckets[key]
        b["total"] += 1
        if t.outcome == "win":
            b["wins"] += 1
        elif t.outcome == "loss":
            b["losses"] += 1
        if t.pnl_pips is not None:
            b["total_pnl_pips"] += t.pnl_pips
        if t.pnl_usd is not None:
            b["total_pnl_usd"] += t.pnl_usd
        if t.rr_achieved is not None:
            b["_rr"].append(t.rr_achieved)
    for v in buckets.values():
        denom = v["wins"] + v["losses"]
        v["win_rate"] = round(v["wins"] / denom * 100, 1) if denom > 0 else None
        v["total_pnl_pips"] = round(v["total_pnl_pips"], 1)
        v["total_pnl_usd"] = round(v["total_pnl_usd"], 2)
        if v["total"] > 0:
            v["avg_pnl_usd"] = round(v["total_pnl_usd"] / v["total"], 2)
        rr = v.pop("_rr")
        v["avg_rr"] = round(sum(rr) / len(rr), 2) if rr else None
    return buckets
