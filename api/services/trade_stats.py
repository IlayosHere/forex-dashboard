"""
api/services/trade_stats.py
---------------------------
Pure functions for computing aggregated trade statistics.

These functions operate on in-memory lists of TradeModel instances and
return plain dicts that match the TradeStatsResponse schema. No DB access,
no side effects.
"""
from __future__ import annotations

from api.models import AccountModel, TradeModel


def calculate_trade_metrics(
    trades: list[TradeModel],
    closed: list[TradeModel],
) -> dict:
    """Compute top-level performance metrics from a list of trades.

    Parameters
    ----------
    trades : list[TradeModel]
        All trades matching the query filters (excluding cancelled).
    closed : list[TradeModel]
        Subset of *trades* with status in ("closed", "breakeven").

    Returns
    -------
    dict with keys matching TradeStatsResponse top-level scalar fields.
    """
    wins = sum(1 for t in closed if t.outcome == "win")
    losses = sum(1 for t in closed if t.outcome == "loss")
    breakevens = sum(1 for t in closed if t.outcome == "breakeven")
    win_rate = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else None

    rr_values = [t.rr_achieved for t in closed if t.rr_achieved is not None]
    avg_rr = round(sum(rr_values) / len(rr_values), 2) if rr_values else None

    pnl_pips_values = [t.pnl_pips for t in closed if t.pnl_pips is not None]
    total_pnl_pips = round(sum(pnl_pips_values), 1)

    pnl_usd_values = [t.pnl_usd for t in closed if t.pnl_usd is not None]
    total_pnl_usd = round(sum(pnl_usd_values), 2)

    best_trade_pnl = max(pnl_pips_values) if pnl_pips_values else None
    worst_trade_pnl = min(pnl_pips_values) if pnl_pips_values else None

    current_streak = _compute_streak(closed)
    profit_factor = _compute_profit_factor(closed)
    avg_hold_time_hours = _compute_avg_hold_time(closed)

    return {
        "total_trades": len(trades),
        "open_trades": sum(1 for t in trades if t.status == "open"),
        "closed_trades": len(closed),
        "wins": wins,
        "losses": losses,
        "breakevens": breakevens,
        "win_rate": win_rate,
        "avg_rr": avg_rr,
        "total_pnl_pips": total_pnl_pips,
        "total_pnl_usd": total_pnl_usd,
        "best_trade_pnl": best_trade_pnl,
        "worst_trade_pnl": worst_trade_pnl,
        "current_streak": current_streak,
        "profit_factor": profit_factor,
        "avg_hold_time_hours": avg_hold_time_hours,
    }


def _compute_streak(closed: list[TradeModel]) -> int:
    """Count consecutive win/loss streak from the most recent closed trade.

    Breakeven trades are skipped — they do not interrupt or contribute to
    streaks.  Returns positive for win streaks, negative for loss streaks,
    0 if no decisive (win/loss) trades exist.
    """
    sorted_closed = sorted(
        closed, key=lambda t: t.close_time or t.open_time, reverse=True,
    )
    decisive = [t for t in sorted_closed if t.outcome in ("win", "loss")]
    if not decisive:
        return 0
    streak_outcome = decisive[0].outcome
    streak = 0
    for t in decisive:
        if t.outcome == streak_outcome:
            streak += 1
        else:
            break
    if streak_outcome == "loss":
        streak = -streak
    return streak


def _compute_profit_factor(closed: list[TradeModel]) -> float | None:
    """Gross profit / gross loss, or None if no losses."""
    gross_profit = sum(
        t.pnl_usd for t in closed if t.pnl_usd is not None and t.pnl_usd > 0
    )
    gross_loss = abs(sum(
        t.pnl_usd for t in closed if t.pnl_usd is not None and t.pnl_usd < 0
    ))
    return round(gross_profit / gross_loss, 2) if gross_loss > 0 else None


def _compute_avg_hold_time(closed: list[TradeModel]) -> float | None:
    """Average hold time in hours across closed trades."""
    hold_times: list[float] = []
    for t in closed:
        if t.open_time and t.close_time:
            delta = t.close_time - t.open_time
            hold_times.append(delta.total_seconds() / 3600)
    return round(sum(hold_times) / len(hold_times), 1) if hold_times else None


def aggregate_by_field(
    closed: list[TradeModel],
    field: str,
) -> dict[str, dict]:
    """Group closed trades by a model field and compute per-group stats.

    Parameters
    ----------
    closed : list[TradeModel]
        Closed trades to aggregate.
    field : str
        Attribute name on TradeModel to group by (e.g. "strategy", "symbol").

    Returns
    -------
    dict mapping field values to {total, wins, losses, win_rate, total_pnl_pips}.
    """
    buckets: dict[str, dict] = {}
    for t in closed:
        key = getattr(t, field)
        if key not in buckets:
            buckets[key] = {
                "total": 0, "wins": 0, "losses": 0,
                "win_rate": None, "total_pnl_pips": 0.0,
                "total_pnl_usd": 0.0,
            }
        buckets[key]["total"] += 1
        if t.outcome == "win":
            buckets[key]["wins"] += 1
        elif t.outcome == "loss":
            buckets[key]["losses"] += 1
        if t.pnl_pips is not None:
            buckets[key]["total_pnl_pips"] += t.pnl_pips
        if t.pnl_usd is not None:
            buckets[key]["total_pnl_usd"] += t.pnl_usd
    for v in buckets.values():
        denom = v["wins"] + v["losses"]
        v["win_rate"] = round(v["wins"] / denom * 100, 1) if denom > 0 else None
        v["total_pnl_pips"] = round(v["total_pnl_pips"], 1)
        v["total_pnl_usd"] = round(v["total_pnl_usd"], 2)
    return buckets


def aggregate_by_account(
    closed: list[TradeModel],
    account_lookup: dict[str, AccountModel],
) -> dict[str, dict]:
    """Group closed trades by account_id with account metadata.

    Parameters
    ----------
    closed : list[TradeModel]
        Closed trades to aggregate.
    account_lookup : dict[str, AccountModel]
        Mapping of account_id to AccountModel for name/type lookups.

    Returns
    -------
    dict mapping account_id to stats dict including account_name and account_type.
    """
    buckets: dict[str, dict] = {}
    for t in closed:
        aid = t.account_id or "__none__"
        if aid not in buckets:
            acct = account_lookup.get(aid)
            buckets[aid] = {
                "account_name": acct.name if acct else None,
                "account_type": acct.account_type if acct else None,
                "instrument_type": acct.instrument_type if acct else None,
                "total": 0, "wins": 0, "losses": 0,
                "win_rate": None, "total_pnl_pips": 0.0,
                "total_pnl_usd": 0.0,
            }
        buckets[aid]["total"] += 1
        if t.outcome == "win":
            buckets[aid]["wins"] += 1
        elif t.outcome == "loss":
            buckets[aid]["losses"] += 1
        if t.pnl_pips is not None:
            buckets[aid]["total_pnl_pips"] += t.pnl_pips
        if t.pnl_usd is not None:
            buckets[aid]["total_pnl_usd"] += t.pnl_usd
    for v in buckets.values():
        denom = v["wins"] + v["losses"]
        v["win_rate"] = round(v["wins"] / denom * 100, 1) if denom > 0 else None
        v["total_pnl_pips"] = round(v["total_pnl_pips"], 1)
        v["total_pnl_usd"] = round(v["total_pnl_usd"], 2)
    return buckets
