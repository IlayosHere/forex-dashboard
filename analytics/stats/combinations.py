"""
analytics/stats/combinations.py
--------------------------------
Ranked pair-combination analysis: scans all confirmed parameter pairs,
finds cells with statistically defensible edge above the baseline win rate,
applies Bonferroni correction, and returns a ranked list.
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

from scipy.stats import norm

from analytics.stats.interaction import build_interaction_grid
from analytics.stats.univariate import wilson_ci

EDGE_BUFFER: float = 0.02
MIN_BONFERRONI_K: int = 1
MAX_BONFERRONI_K: int = 200

_BONFERRONI_ALPHA: float = 0.05
_RAW_Z: float = 1.96


def find_top_combinations(
    enriched: list[dict[str, Any]],
    confirmed_params: list[dict[str, str]],
    overall_win_rate: float,
    limit: int = 20,
    min_cell_n: int = 25,
) -> dict[str, Any]:
    """Scan all confirmed param pairs for cells with edge above baseline.

    Returns dict with keys:
        items           list[dict] — ranked TopCombination-shaped dicts
        pairs_scanned   int
        cells_evaluated int
        reason          str | None — "insufficient_confirmed_params" |
                        "no_edge_found" | None
    """
    if len(confirmed_params) < 2:
        return {
            "items": [],
            "pairs_scanned": 0,
            "cells_evaluated": 0,
            "reason": "insufficient_confirmed_params",
        }

    candidates, pairs_scanned = _enumerate_pair_candidates(
        enriched, confirmed_params, overall_win_rate, min_cell_n
    )
    cells_evaluated = len(candidates)

    if cells_evaluated == 0:
        return {
            "items": [],
            "pairs_scanned": pairs_scanned,
            "cells_evaluated": 0,
            "reason": "no_edge_found",
        }

    z_adj = _bonferroni_z(cells_evaluated)
    surviving = _apply_adjusted_ci(candidates, z_adj, overall_win_rate)

    if not surviving:
        return {
            "items": [],
            "pairs_scanned": pairs_scanned,
            "cells_evaluated": cells_evaluated,
            "reason": "no_edge_found",
        }

    result = _rank_and_trim(surviving, limit)
    return {
        "items": result,
        "pairs_scanned": pairs_scanned,
        "cells_evaluated": cells_evaluated,
        "reason": None,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _enumerate_pair_candidates(
    enriched: list[dict[str, Any]],
    confirmed_params: list[dict[str, str]],
    overall_win_rate: float,
    min_cell_n: int,
) -> tuple[list[dict[str, Any]], int]:
    """Generate all unordered param pairs and collect eligible edge cells."""
    candidates: list[dict[str, Any]] = []
    pairs_scanned = 0

    sorted_params = sorted(confirmed_params, key=lambda p: p["name"])

    for param_a, param_b in combinations(sorted_params, 2):
        pairs_scanned += 1
        _, __, cells = build_interaction_grid(
            enriched,
            param_a["name"],
            param_a["dtype"],
            param_b["name"],
            param_b["dtype"],
        )
        for cell in cells:
            if cell.total < min_cell_n:
                continue
            cell_wr = cell.wins / cell.total
            ci_lo, ci_hi = wilson_ci(cell.wins, cell.total, z=_RAW_Z)
            candidate = _build_candidate(
                param_a, param_b, cell, cell_wr, ci_lo, ci_hi, overall_win_rate
            )
            if candidate is not None:
                candidates.append(candidate)

    return candidates, pairs_scanned


def _build_candidate(
    param_a: dict[str, str],
    param_b: dict[str, str],
    cell: Any,
    cell_wr: float,
    ci_lo: float,
    ci_hi: float,
    overall_win_rate: float,
) -> dict[str, Any] | None:
    """Return a candidate dict if the cell meets the raw eligibility threshold."""
    threshold = overall_win_rate + EDGE_BUFFER
    neg_threshold = overall_win_rate - EDGE_BUFFER

    if cell_wr > threshold and ci_lo > threshold:
        direction = "positive"
    elif cell_wr < neg_threshold and ci_hi < neg_threshold:
        direction = "negative"
    else:
        return None

    losses = cell.total - cell.wins
    return {
        "param_a": param_a["name"],
        "bucket_a": cell.bucket_a,
        "param_b": param_b["name"],
        "bucket_b": cell.bucket_b,
        "wins": cell.wins,
        "losses": losses,
        "total": cell.total,
        "win_rate": cell_wr,
        "edge": cell_wr - overall_win_rate,
        "direction": direction,
        "ci_lo_raw": ci_lo,
        "ci_hi_raw": ci_hi,
    }


def _bonferroni_z(k_cells: int) -> float:
    """Compute Bonferroni-adjusted z critical value for k simultaneous tests."""
    k = max(MIN_BONFERRONI_K, min(k_cells, MAX_BONFERRONI_K))
    return float(norm.ppf(1 - _BONFERRONI_ALPHA / (2 * k)))


def _apply_adjusted_ci(
    candidates: list[dict[str, Any]],
    z_adj: float,
    overall_win_rate: float,
) -> list[dict[str, Any]]:
    """Recompute Wilson CI with Bonferroni z; drop candidates that no longer pass."""
    surviving: list[dict[str, Any]] = []
    threshold = overall_win_rate + EDGE_BUFFER
    neg_threshold = overall_win_rate - EDGE_BUFFER

    for cand in candidates:
        ci_lo_adj, ci_hi_adj = wilson_ci(cand["wins"], cand["total"], z=z_adj)
        direction = cand["direction"]

        if direction == "positive" and ci_lo_adj <= threshold:
            continue
        if direction == "negative" and ci_hi_adj >= neg_threshold:
            continue

        score = (
            ci_lo_adj - overall_win_rate
            if direction == "positive"
            else overall_win_rate - ci_hi_adj
        )
        surviving.append({
            **cand,
            "ci_lo_adjusted": ci_lo_adj,
            "ci_hi_adjusted": ci_hi_adj,
            "score": score,
        })

    return surviving


def _rank_and_trim(
    candidates: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    """Sort by score descending, assign 1-based rank, trim to limit."""
    sorted_candidates = sorted(candidates, key=lambda c: c["score"], reverse=True)
    result: list[dict[str, Any]] = []
    for rank, cand in enumerate(sorted_candidates[:limit], start=1):
        result.append({**cand, "rank": rank})
    return result
