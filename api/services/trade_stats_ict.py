"""
api/services/trade_stats_ict.py
--------------------------------
Pure aggregation functions for ICT (Inner Circle Trader) statistics.

All functions accept pre-filtered lists of TradeModel instances and return
structured dicts that map to IctStatsResponse. No DB access, no side effects.

MNQ session classification uses a fixed UTC-4 offset (EDT) approximation since
the majority of MNQ trading occurs during US daylight hours.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from api.models import TradeModel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Session boundaries — stored times are ET (logged by user, no UTC conversion)
# ---------------------------------------------------------------------------

# Sessions defined as (key, start_minutes_et_inclusive, end_minutes_et_exclusive)
# AM  : 09:30–11:30 ET
# Lunch: 11:30–13:00 ET
# PM  : 13:00–16:00 ET
# Other: everything outside those windows
_MNQ_SESSION_RANGES: list[tuple[str, int, int]] = [
    ("am",    9 * 60 + 30,  11 * 60 + 30),
    ("lunch", 11 * 60 + 30, 13 * 60),
    ("pm",    13 * 60,      16 * 60),
]

ALL_MNQ_SESSIONS: list[str] = ["am", "lunch", "pm", "other"]

_CLOSED_STATUSES: frozenset[str] = frozenset({"closed", "breakeven"})


# ---------------------------------------------------------------------------
# Session classifier
# ---------------------------------------------------------------------------

def classify_mnq_session(open_time_utc: datetime) -> str:
    """Map a stored open_time to an MNQ session.

    MNQ trades are logged in ET by the user and stored without timezone conversion,
    so the stored hour/minute IS the ET time — no offset needed.
    AM: 09:30–11:30 | Lunch: 11:30–13:00 | PM: 13:00–16:00 | Other: outside.
    """
    et_minutes = open_time_utc.hour * 60 + open_time_utc.minute
    for session, start, end in _MNQ_SESSION_RANGES:
        if start <= et_minutes < end:
            return session
    return "other"


# ---------------------------------------------------------------------------
# Bucket stats helper
# ---------------------------------------------------------------------------

def _bucket_stats(trades: list[TradeModel]) -> dict[str, Any]:
    """Compute wins/losses/P&L/R:R stats for a group of trades.

    Only closed/breakeven trades count toward wins, losses, and win_rate.
    All trades contribute to total. Returns a dict matching IctBucketStats.
    """
    closed = [t for t in trades if t.status in _CLOSED_STATUSES]
    wins = sum(1 for t in closed if t.outcome == "win")
    losses = sum(1 for t in closed if t.outcome == "loss")
    decisive = wins + losses
    win_rate = round(wins / decisive * 100.0, 1) if decisive > 0 else None

    pnl_values = [t.pnl_usd for t in trades if t.pnl_usd is not None]
    total_pnl = round(sum(pnl_values), 2)
    avg_pnl = round(total_pnl / len(pnl_values), 2) if pnl_values else None

    rr_values = [t.rr_achieved for t in trades if t.rr_achieved is not None]
    avg_rr = round(sum(rr_values) / len(rr_values), 2) if rr_values else None

    return {
        "total": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "total_pnl_usd": total_pnl,
        "avg_pnl_usd": avg_pnl,
        "avg_rr": avg_rr,
    }


def _zero_bucket() -> dict[str, Any]:
    """Return an empty bucket dict for sessions with zero trades."""
    return {
        "total": 0, "wins": 0, "losses": 0,
        "win_rate": None, "total_pnl_usd": 0.0,
        "avg_pnl_usd": None, "avg_rr": None,
    }


# ---------------------------------------------------------------------------
# Aggregation functions
# ---------------------------------------------------------------------------

def aggregate_by_ict_field(
    trades: list[TradeModel],
    field: str,
) -> dict[str, dict[str, Any]]:
    """Group trades by an ICT field value and compute bucket stats per group.

    Trades where the field value is None are skipped.
    Returns {field_value: IctBucketStats dict}.
    """
    buckets: dict[str, list[TradeModel]] = {}
    for trade in trades:
        value = getattr(trade, field, None)
        if value is None:
            continue
        key = str(value)
        buckets.setdefault(key, []).append(trade)
    return {k: _bucket_stats(v) for k, v in buckets.items()}


def aggregate_by_mnq_session(
    trades: list[TradeModel],
) -> dict[str, dict[str, Any]]:
    """Group trades by MNQ trading session derived from open_time.

    All five sessions are always present in the result; sessions with no trades
    return zero-value buckets.
    Returns {session_key: IctBucketStats dict}.
    """
    buckets: dict[str, list[TradeModel]] = {s: [] for s in ALL_MNQ_SESSIONS}
    for trade in trades:
        if trade.open_time is None:
            continue
        session = classify_mnq_session(trade.open_time)
        buckets[session].append(trade)
    return {
        s: _bucket_stats(v) if v else _zero_bucket()
        for s, v in buckets.items()
    }


def aggregate_boolean_flags(
    trades: list[TradeModel],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Compute bucket stats split by True/False for SMT and TDO boolean flags.

    Trades where either flag is None are excluded from that flag's comparison.
    Returns {flag_name: {true: IctBucketStats, false: IctBucketStats}}.
    """
    smt_true: list[TradeModel] = []
    smt_false: list[TradeModel] = []
    tdo_true: list[TradeModel] = []
    tdo_false: list[TradeModel] = []

    for trade in trades:
        if trade.ict_smt_present is not None:
            (smt_true if trade.ict_smt_present else smt_false).append(trade)
        if trade.ict_tdo_aligned is not None:
            (tdo_true if trade.ict_tdo_aligned else tdo_false).append(trade)

    return {
        "smt_present": {
            "true": _bucket_stats(smt_true),
            "false": _bucket_stats(smt_false),
        },
        "tdo_aligned": {
            "true": _bucket_stats(tdo_true),
            "false": _bucket_stats(tdo_false),
        },
    }


def build_combo_matrix(
    trades: list[TradeModel],
) -> list[dict[str, Any]]:
    """Cross-tabulate setup_type x (smt_present, tdo_aligned).

    Returns one entry per unique (setup_type, smt_present, tdo_aligned) combo
    that has at least one trade, sorted by win_rate descending (None last).
    Trades where ict_setup_type is None are skipped entirely.
    """
    ComboKey = tuple[str, bool | None, bool | None]
    groups: dict[ComboKey, list[TradeModel]] = {}

    for trade in trades:
        if trade.ict_setup_type is None:
            continue
        key: ComboKey = (
            trade.ict_setup_type,
            trade.ict_smt_present,
            trade.ict_tdo_aligned,
        )
        groups.setdefault(key, []).append(trade)

    rows: list[dict[str, Any]] = []
    for (setup_type, smt, tdo), group in groups.items():
        stats = _bucket_stats(group)
        rows.append({
            "setup_type": setup_type,
            "smt_present": smt,
            "tdo_aligned": tdo,
            "total": stats["total"],
            "wins": stats["wins"],
            "losses": stats["losses"],
            "win_rate": stats["win_rate"],
            "total_pnl_usd": stats["total_pnl_usd"],
            "avg_rr": stats["avg_rr"],
        })

    rows.sort(key=lambda r: (r["win_rate"] is None, -(r["win_rate"] or 0.0)))
    return rows


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def compute_ict_stats(trades: list[TradeModel]) -> dict[str, Any]:
    """Orchestrate all ICT aggregations and return the full IctStatsResponse dict.

    Filters the input list to futures_mnq instrument_type before delegating to
    sub-functions. Callers may pass a pre-filtered list for efficiency.
    """
    mnq_trades = [t for t in trades if t.instrument_type == "futures_mnq"]
    logger.debug("compute_ict_stats: %d MNQ trades", len(mnq_trades))

    closed = [t for t in mnq_trades if t.status in _CLOSED_STATUSES]
    wins = sum(1 for t in closed if t.outcome == "win")
    losses = sum(1 for t in closed if t.outcome == "loss")
    decisive = wins + losses
    win_rate = round(wins / decisive * 100.0, 1) if decisive > 0 else None

    return {
        "total_trades": len(mnq_trades),
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "by_setup_type": aggregate_by_ict_field(mnq_trades, "ict_setup_type"),
        "by_tp_target": aggregate_by_ict_field(mnq_trades, "ict_tp_target"),
        "by_ifvg_timeframe": aggregate_by_ict_field(mnq_trades, "ict_ifvg_timeframe"),
        "by_mnq_session": aggregate_by_mnq_session(mnq_trades),
        "boolean_flags": aggregate_boolean_flags(mnq_trades),
        "combo_matrix": build_combo_matrix(mnq_trades),
    }
