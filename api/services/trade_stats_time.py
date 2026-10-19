"""
api/services/trade_stats_time.py
--------------------------------
Time-of-day edge analysis for ICT futures trades.

Answers: which part of the NY session am I best in, which setups and IFVG
timeframes work in which phase, and where are my weakest cells. Pure functions
over pre-filtered TradeModel lists — no DB access, no side effects.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from api.models import TradeModel
from api.services.ict_classifiers import (
    ALL_NY_PHASES,
    all_macro_labels,
    all_time_slices,
    classify_macro,
    classify_ny_phase,
    classify_time_slice,
)
from api.services.trade_stats_ict import bucket_stats, filter_futures, zero_bucket

logger = logging.getLogger(__name__)

MIN_SAMPLE = 3          # cells with fewer trades are shown but never ranked
_INSIGHTS_PER_KIND = 3
_WEEKDAYS: list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

RowFn = Callable[[TradeModel], str | None]

# matrix key -> (human dimension label, row-value extractor)
_MATRIX_DIMENSIONS: dict[str, tuple[str, RowFn]] = {
    "all": ("All trades", lambda t: "All trades"),
    "setup_type": ("Setup", lambda t: t.ict_setup_type),
    "ifvg_timeframe": ("IFVG timeframe", lambda t: t.ict_ifvg_timeframe),
    "direction": ("Direction", lambda t: t.direction.lower() if t.direction else None),
    "weekday": ("Weekday", lambda t: _WEEKDAYS[t.open_time.weekday()]),
    "htf_bias": ("HTF bias", lambda t: t.ict_htf_bias),
    "tp_target": ("TP target", lambda t: t.ict_tp_target),
}


def _bucketed(
    trades: list[TradeModel], labels: list[str], classify: Callable[[datetime], str],
) -> dict[str, dict[str, Any]]:
    """Group trades by classify(open_time); every label appears, empty ones zeroed."""
    groups: dict[str, list[TradeModel]] = {label: [] for label in labels}
    for trade in trades:
        groups.setdefault(classify(trade.open_time), []).append(trade)
    return {k: bucket_stats(v) if v else zero_bucket() for k, v in groups.items()}


def build_matrix(trades: list[TradeModel], row_fn: RowFn) -> list[dict[str, Any]]:
    """Cross-tab row value x NY phase; only cells with at least one trade are emitted."""
    cells: dict[tuple[str, str], list[TradeModel]] = {}
    for trade in trades:
        row = row_fn(trade)
        if row is None:
            continue
        cells.setdefault((str(row), classify_ny_phase(trade.open_time)), []).append(trade)
    return [
        {"row": row, "phase": phase, "stats": bucket_stats(group)}
        for (row, phase), group in sorted(cells.items())
    ]


def build_insights(matrices: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Rank the best and worst (row x phase) cells by expectancy, ignoring tiny samples."""
    candidates: list[dict[str, Any]] = []
    for key, cells in matrices.items():
        dimension = _MATRIX_DIMENSIONS[key][0]
        for cell in cells:
            stats = cell["stats"]
            if stats["total"] < MIN_SAMPLE or stats["expectancy_r"] is None:
                continue
            candidates.append({"dimension": dimension, **cell})
    candidates.sort(key=lambda c: c["stats"]["expectancy_r"], reverse=True)
    strengths = [c for c in candidates if c["stats"]["expectancy_r"] > 0]
    weaknesses = [c for c in reversed(candidates) if c["stats"]["expectancy_r"] < 0]
    return (
        [{"kind": "strength", **c} for c in strengths[:_INSIGHTS_PER_KIND]]
        + [{"kind": "weakness", **c} for c in weaknesses[:_INSIGHTS_PER_KIND]]
    )


def compute_time_edge(trades: list[TradeModel]) -> dict[str, Any]:
    """Build the full time-of-day edge payload from MNQ/MES trades."""
    timed = [t for t in filter_futures(trades) if t.open_time is not None]
    logger.debug("compute_time_edge: %d timed trades", len(timed))
    matrices = {key: build_matrix(timed, fn) for key, (_, fn) in _MATRIX_DIMENSIONS.items()}
    return {
        "by_ny_phase": _bucketed(timed, ALL_NY_PHASES, classify_ny_phase),
        "by_time_slice": _bucketed(timed, all_time_slices(), classify_time_slice),
        "by_macro": _bucketed(timed, [*all_macro_labels(), "outside"], classify_macro),
        "matrices": matrices,
        "insights": build_insights(matrices),
        "min_sample": MIN_SAMPLE,
    }
