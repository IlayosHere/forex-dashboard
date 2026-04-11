"""
analytics/stats/filters.py
---------------------------
Functions to split enriched signals into buckets for statistical analysis.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def quintile_split(
    enriched: list[dict[str, Any]],
    param_name: str,
    n_buckets: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    """Split signals into equal-sized buckets by numeric param percentiles.

    Parameters
    ----------
    enriched : list[dict]
        Enriched signal dicts, each with a ``params`` sub-dict.
    param_name : str
        Key inside ``params`` to bucket by.
    n_buckets : int
        Number of quantile buckets (default 5).

    Returns
    -------
    dict mapping bucket label ``"Q{n} ({lo:.2f}-{hi:.2f})"`` to signal list.
    """
    pairs = _extract_param_pairs(enriched, param_name)
    if not pairs:
        return {}

    pairs.sort(key=lambda t: t[0])
    values = [v for v, _ in pairs]

    boundaries = _compute_boundaries(values, n_buckets)

    buckets: dict[str, list[dict[str, Any]]] = {}
    for val, sig in pairs:
        idx = _assign_bucket(val, boundaries, n_buckets)
        lo, hi = boundaries[idx], boundaries[idx + 1]
        label = f"Q{idx + 1} ({lo:.2f}-{hi:.2f})"
        buckets.setdefault(label, []).append(sig)

    return buckets


def category_split(
    enriched: list[dict[str, Any]],
    param_name: str,
) -> dict[str, list[dict[str, Any]]]:
    """Group signals by categorical param value.

    Parameters
    ----------
    enriched : list[dict]
        Enriched signal dicts.
    param_name : str
        Key inside ``params`` to group by.

    Returns
    -------
    dict mapping category value (as str) to signal list.
    """
    buckets: dict[str, list[dict[str, Any]]] = {}
    for sig in enriched:
        val = sig.get("params", {}).get(param_name)
        if val is None:
            continue
        key = str(val)
        buckets.setdefault(key, []).append(sig)
    return buckets


def filter_min_bucket(
    buckets: dict[str, list[dict[str, Any]]],
    min_size: int = 30,
) -> dict[str, list[dict[str, Any]]]:
    """Remove buckets with fewer than *min_size* signals."""
    filtered = {k: v for k, v in buckets.items() if len(v) >= min_size}
    removed = len(buckets) - len(filtered)
    if removed:
        logger.debug("Filtered out %d buckets below min_size=%d", removed, min_size)
    return filtered


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_param_pairs(
    enriched: list[dict[str, Any]],
    param_name: str,
) -> list[tuple[float, dict[str, Any]]]:
    """Return (value, signal) pairs, skipping None values."""
    pairs: list[tuple[float, dict[str, Any]]] = []
    for sig in enriched:
        val = sig.get("params", {}).get(param_name)
        if val is not None:
            pairs.append((float(val), sig))
    return pairs


def _compute_boundaries(
    values: list[float],
    n_buckets: int,
) -> list[float]:
    """Compute n_buckets+1 percentile boundaries from sorted values."""
    percentiles = [i * (100 / n_buckets) for i in range(n_buckets + 1)]
    bounds = list(np.percentile(values, percentiles).astype(float))
    return bounds


def _assign_bucket(
    val: float,
    boundaries: list[float],
    n_buckets: int,
) -> int:
    """Return 0-based bucket index for a value given boundaries."""
    for i in range(n_buckets - 1):
        if val < boundaries[i + 1]:
            return i
    return n_buckets - 1
