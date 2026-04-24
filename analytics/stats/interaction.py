"""
analytics/stats/interaction.py
-------------------------------
Grid-building logic for the 2D interaction heatmap endpoint.
"""
from __future__ import annotations

from typing import Any

from analytics.schemas import InteractionCell
from analytics.stats.filters import category_split, quintile_split
from analytics.types import LOSS_RESOLUTION, WIN_RESOLUTION

_SPARSE_THRESHOLD = 15


def _split_param(
    enriched: list[dict[str, Any]],
    param_name: str,
    dtype: str,
) -> dict[str, list[dict[str, Any]]]:
    """Split enriched signals into buckets for one parameter."""
    if dtype in ("str", "bool"):
        return category_split(enriched, param_name)
    return quintile_split(enriched, param_name)


def _ordered_bucket_keys(buckets: dict[str, list[dict[str, Any]]], dtype: str) -> list[str]:
    """Return ordered bucket keys: Q-order for numeric, alphabetical for categorical."""
    if dtype in ("float", "int"):
        return sorted(buckets.keys(), key=lambda k: int(k[1]) if k and k[0] == "Q" else 0)
    return sorted(buckets.keys())


def build_interaction_grid(
    enriched: list[dict[str, Any]],
    param_a: str,
    dtype_a: str,
    param_b: str,
    dtype_b: str,
) -> tuple[list[str], list[str], list[InteractionCell]]:
    """Build a 2D win/loss grid for two parameters.

    Returns
    -------
    tuple of (buckets_a, buckets_b, cells)
        buckets_a / buckets_b — ordered label lists.
        cells — one InteractionCell per (bucket_a, bucket_b) pair.
    """
    buckets_a = _split_param(enriched, param_a, dtype_a)
    buckets_b = _split_param(enriched, param_b, dtype_b)

    ordered_a = _ordered_bucket_keys(buckets_a, dtype_a)
    ordered_b = _ordered_bucket_keys(buckets_b, dtype_b)

    # Build a lookup: signal id → bucket_b label
    signal_to_b: dict[str, str] = {}
    for label_b, sigs in buckets_b.items():
        for sig in sigs:
            signal_to_b[sig["id"]] = label_b

    grid: dict[tuple[str, str], list[int]] = {}  # [wins, losses]
    for label_a, sigs_a in buckets_a.items():
        for sig in sigs_a:
            label_b = signal_to_b.get(sig["id"])
            if label_b is None:
                continue
            key = (label_a, label_b)
            if key not in grid:
                grid[key] = [0, 0]
            res = sig.get("resolution")
            if res == WIN_RESOLUTION:
                grid[key][0] += 1
            elif res == LOSS_RESOLUTION:
                grid[key][1] += 1

    cells: list[InteractionCell] = []
    for label_a in ordered_a:
        for label_b in ordered_b:
            wins, losses = grid.get((label_a, label_b), [0, 0])
            total = wins + losses
            win_rate = (wins / total) if total >= _SPARSE_THRESHOLD else None
            cells.append(InteractionCell(
                bucket_a=label_a,
                bucket_b=label_b,
                wins=wins,
                losses=losses,
                total=total,
                win_rate=win_rate,
            ))

    return ordered_a, ordered_b, cells
