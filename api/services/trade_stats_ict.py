"""
api/services/trade_stats_ict.py
--------------------------------
Pure aggregation functions for ICT statistics.

All functions accept pre-filtered TradeModel lists. No DB access, no side effects.
Time classification is delegated to ict_classifiers.
"""
from __future__ import annotations

import logging
from typing import Any

from api.models import TradeModel
from api.services.ict_classifiers import (
    ALL_MNQ_SESSIONS,
    classify_killzone,
    classify_mnq_session,
)
from shared.ict_taxonomy import KILLZONE_BUCKETS

logger = logging.getLogger(__name__)

_CLOSED_STATUSES: frozenset[str] = frozenset({"closed", "breakeven"})


# ---------------------------------------------------------------------------
# Bucket stats helpers
# ---------------------------------------------------------------------------

def _expectancy_r(closed: list[TradeModel]) -> float | None:
    """Expectancy in R: (win% × avg_win_R) − (loss% × avg_loss_R)."""
    wins = [t for t in closed if t.outcome == "win" and t.rr_achieved is not None]
    losses = [t for t in closed if t.outcome == "loss" and t.rr_achieved is not None]
    if not wins and not losses:
        return None
    n = len(wins) + len(losses)
    wr = len(wins) / n
    avg_w = sum(t.rr_achieved for t in wins) / len(wins) if wins else 0.0  # type: ignore[arg-type]
    avg_l = sum(abs(t.rr_achieved) for t in losses) / len(losses) if losses else 0.0  # type: ignore[arg-type]
    return round(wr * avg_w - (1 - wr) * avg_l, 2)


def _bucket_stats(trades: list[TradeModel]) -> dict[str, Any]:
    """Aggregate wins/losses/P&L/R:R/expectancy_r for a group of trades."""
    closed = [t for t in trades if t.status in _CLOSED_STATUSES]
    wins = sum(1 for t in closed if t.outcome == "win")
    losses = sum(1 for t in closed if t.outcome == "loss")
    decisive = wins + losses
    win_rate = round(wins / decisive * 100.0, 1) if decisive > 0 else None
    pnl_vals = [t.pnl_usd for t in trades if t.pnl_usd is not None]
    total_pnl = round(sum(pnl_vals), 2)
    avg_pnl = round(total_pnl / len(pnl_vals), 2) if pnl_vals else None
    rr_vals = [t.rr_achieved for t in trades if t.rr_achieved is not None]
    avg_rr = round(sum(rr_vals) / len(rr_vals), 2) if rr_vals else None
    return {
        "total": len(trades), "wins": wins, "losses": losses,
        "win_rate": win_rate, "total_pnl_usd": total_pnl,
        "avg_pnl_usd": avg_pnl, "avg_rr": avg_rr,
        "expectancy_r": _expectancy_r(closed),
    }


def _zero_bucket() -> dict[str, Any]:
    """Empty bucket for sessions/killzones with no trades."""
    return {
        "total": 0, "wins": 0, "losses": 0, "win_rate": None,
        "total_pnl_usd": 0.0, "avg_pnl_usd": None, "avg_rr": None,
        "expectancy_r": None,
    }


# ---------------------------------------------------------------------------
# Aggregation functions
# ---------------------------------------------------------------------------

def aggregate_by_ict_field(trades: list[TradeModel], field: str) -> dict[str, dict[str, Any]]:
    """Group trades by a string ICT field; skip None values."""
    buckets: dict[str, list[TradeModel]] = {}
    for trade in trades:
        value = getattr(trade, field, None)
        if value is None:
            continue
        buckets.setdefault(str(value), []).append(trade)
    return {k: _bucket_stats(v) for k, v in buckets.items()}


def aggregate_by_mnq_session(trades: list[TradeModel]) -> dict[str, dict[str, Any]]:
    """Group trades by coarse MNQ session derived from open_time."""
    buckets: dict[str, list[TradeModel]] = {s: [] for s in ALL_MNQ_SESSIONS}
    for trade in trades:
        if trade.open_time is None:
            continue
        buckets[classify_mnq_session(trade.open_time)].append(trade)
    return {s: _bucket_stats(v) if v else _zero_bucket() for s, v in buckets.items()}


def aggregate_by_killzone(trades: list[TradeModel]) -> dict[str, dict[str, Any]]:
    """Group trades by ICT killzone window derived from open_time."""
    buckets: dict[str, list[TradeModel]] = {k: [] for k in KILLZONE_BUCKETS}
    for trade in trades:
        if trade.open_time is None:
            continue
        buckets[classify_killzone(trade.open_time)].append(trade)
    return {k: _bucket_stats(v) if v else _zero_bucket() for k, v in buckets.items()}


def aggregate_boolean_flags(trades: list[TradeModel]) -> dict[str, dict[str, dict[str, Any]]]:
    """True/False split for SMT and TDO boolean flags."""
    smt_t: list[TradeModel] = []
    smt_f: list[TradeModel] = []
    tdo_t: list[TradeModel] = []
    tdo_f: list[TradeModel] = []
    for trade in trades:
        if trade.ict_smt_present is not None:
            (smt_t if trade.ict_smt_present else smt_f).append(trade)
        if trade.ict_tdo_aligned is not None:
            (tdo_t if trade.ict_tdo_aligned else tdo_f).append(trade)
    return {
        "smt_present": {"true": _bucket_stats(smt_t), "false": _bucket_stats(smt_f)},
        "tdo_aligned":  {"true": _bucket_stats(tdo_t), "false": _bucket_stats(tdo_f)},
    }


def build_combo_matrix(trades: list[TradeModel]) -> list[dict[str, Any]]:
    """Cross-tabulate setup_type x mnq_session x htf_bias, sorted by expectancy_r desc."""
    ComboKey = tuple[str, str, str | None]
    groups: dict[ComboKey, list[TradeModel]] = {}
    for trade in trades:
        if trade.ict_setup_type is None:
            continue
        session = classify_mnq_session(trade.open_time) if trade.open_time else "other"
        key: ComboKey = (trade.ict_setup_type, session, trade.ict_htf_bias)
        groups.setdefault(key, []).append(trade)
    rows: list[dict[str, Any]] = []
    for (setup_type, session, htf_bias), group in groups.items():
        s = _bucket_stats(group)
        rows.append({
            "setup_type": setup_type, "mnq_session": session, "htf_bias": htf_bias,
            "total": s["total"], "wins": s["wins"], "losses": s["losses"],
            "win_rate": s["win_rate"], "total_pnl_usd": s["total_pnl_usd"],
            "avg_rr": s["avg_rr"], "expectancy_r": s["expectancy_r"],
        })
    rows.sort(key=lambda r: (r["expectancy_r"] is None, -(r["expectancy_r"] or 0.0)))
    return rows


# ---------------------------------------------------------------------------
# IFVG bars × timeframe matrix
# ---------------------------------------------------------------------------

_BARS_CAP = 10  # bars > this are bucketed as "10+"


def _bars_label(bars: int) -> str:
    return f"{bars}" if bars <= _BARS_CAP else "10+"


def aggregate_ifvg_bars_matrix(trades: list[TradeModel]) -> list[dict[str, Any]]:
    """Cross-tabulate ict_ifvg_bars × ict_ifvg_timeframe for MNQ trades.

    Returns a flat list of rows — one per (bars_label, timeframe) cell that
    has at least one trade. Frontend pivots this into the 2-D table.
    """
    Cell = tuple[str, str]
    groups: dict[Cell, list[TradeModel]] = {}
    for trade in trades:
        if trade.ict_ifvg_bars is None or trade.ict_ifvg_timeframe is None:
            continue
        key: Cell = (_bars_label(trade.ict_ifvg_bars), trade.ict_ifvg_timeframe)
        groups.setdefault(key, []).append(trade)

    rows: list[dict[str, Any]] = []
    for (bars_label, timeframe), group in groups.items():
        s = _bucket_stats(group)
        rows.append({
            "bars_label": bars_label,
            "timeframe": timeframe,
            **s,
        })
    rows.sort(key=lambda r: (
        int(r["bars_label"].rstrip("+")) if r["bars_label"] != "10+" else 11,
        r["timeframe"],
    ))
    return rows


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def compute_ict_stats(trades: list[TradeModel]) -> dict[str, Any]:
    """Orchestrate all ICT aggregations and return the full IctStatsResponse dict."""
    mnq = [t for t in trades if t.instrument_type == "futures_mnq"]
    logger.debug("compute_ict_stats: %d MNQ trades", len(mnq))
    closed = [t for t in mnq if t.status in _CLOSED_STATUSES]
    wins = sum(1 for t in closed if t.outcome == "win")
    losses = sum(1 for t in closed if t.outcome == "loss")
    decisive = wins + losses
    return {
        "total_trades": len(mnq),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / decisive * 100.0, 1) if decisive > 0 else None,
        "by_setup_type":      aggregate_by_ict_field(mnq, "ict_setup_type"),
        "by_tp_target":       aggregate_by_ict_field(mnq, "ict_tp_target"),
        "by_ifvg_timeframe":  aggregate_by_ict_field(mnq, "ict_ifvg_timeframe"),
        "by_mnq_session":     aggregate_by_mnq_session(mnq),
        "by_htf_bias":        aggregate_by_ict_field(mnq, "ict_htf_bias"),
        "by_killzone":        aggregate_by_killzone(mnq),
        "boolean_flags":      aggregate_boolean_flags(mnq),
        "combo_matrix":       build_combo_matrix(mnq),
        "ifvg_bars_matrix":   aggregate_ifvg_bars_matrix(mnq),
    }
