"""
analytics/stats/classification.py
---------------------------------
CI-based classification framework for univariate analytics.

Replaces p-value-only classification with a two-proportion confidence
interval approach that combines statistical evidence and effect size in
one principled statistic. See ``two_proportion_ci`` in
``analytics/stats/univariate.py`` for the underlying math.
"""
from __future__ import annotations

from typing import Any

from analytics.stats.univariate import two_proportion_ci
from analytics.types import LOSS_RESOLUTION, WIN_RESOLUTION

# Effect-size cutoff in win-rate fraction (0.05 = 5pp). NOT a p-value alpha.
# SIGNIFICANCE_THRESHOLD in report.py is the p-value alpha — the two are
# numerically equal by coincidence but semantically unrelated.
ECONOMIC_THRESHOLD = 0.05
Z_CRITICAL: dict[int, float] = {
    1: 1.96,
    2: 2.24,
    3: 2.39,
    4: 2.50,
    5: 2.58,
    6: 2.64,
}
Z_CRITICAL_FALLBACK = 2.64

CI_LEVELS = frozenset({
    "strong_positive", "strong_negative",
    "real_positive", "real_negative",
    "suggestive_positive", "suggestive_negative",
    "hint_positive", "hint_negative",
    "none",
})


def z_critical(k: int) -> float:
    """Return Bonferroni-corrected z-critical for picking the most extreme of k buckets."""
    return Z_CRITICAL.get(k, Z_CRITICAL_FALLBACK)


def classify_from_ci(delta: float, ci_lo: float, ci_hi: float) -> str:
    """Classify a delta + CI into one of nine CI_LEVELS strings.

    Symmetric nine-level ladder (see project spec):
        strong_*      — CI entirely beyond +/-T
        real_*        — CI entirely on one side of 0 (doesn't clear T)
        suggestive_*  — CI straddles 0, observed |delta| >= 2T
        hint_*        — CI straddles 0, observed |delta| >= T
        none          — everything else
    """
    t = ECONOMIC_THRESHOLD
    if ci_lo >= t:
        return "strong_positive"
    if ci_hi <= -t:
        return "strong_negative"
    if ci_lo > 0:
        return "real_positive"
    if ci_hi < 0:
        return "real_negative"
    if delta >= 2 * t:
        return "suggestive_positive"
    if delta <= -2 * t:
        return "suggestive_negative"
    if delta >= t:
        return "hint_positive"
    if delta <= -t:
        return "hint_negative"
    return "none"


def compute_bucket_ci(
    wins_b: int,
    n_b: int,
    wins_total: int,
    n_total: int,
    z: float,
) -> tuple[float, float, float] | None:
    """Compute (delta, ci_lo, ci_hi) for one bucket vs the rest."""
    wins_rest = wins_total - wins_b
    n_rest = n_total - n_b
    return two_proportion_ci(wins_b, n_b, wins_rest, n_rest, z=z)


def best_bucket_analysis(
    buckets: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    """Pick the driver bucket (largest |delta|) and classify.

    Rule 2 tie-breaker: when two buckets have identical |delta|, pick
    the one with the smaller ``n_b`` (more uncertain, more conservative).

    Returns
    -------
    dict with keys ``delta``, ``ci_lo``, ``ci_hi``, ``best_bucket``,
    ``level`` — or ``None`` if ``buckets`` is empty.
    """
    if not buckets:
        return None

    counts = _bucket_counts(buckets)
    wins_total = sum(w for w, _ in counts.values())
    n_total = sum(n for _, n in counts.values())
    if n_total <= 0:
        return None

    k = len(buckets)
    z = z_critical(k)

    best = _select_best(counts, wins_total, n_total, z)
    if best is None:
        return None

    label, delta, ci_lo, ci_hi = best
    return {
        "delta": delta,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "best_bucket": label,
        "level": classify_from_ci(delta, ci_lo, ci_hi),
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _bucket_counts(
    buckets: dict[str, list[dict[str, Any]]],
) -> dict[str, tuple[int, int]]:
    """Return {label: (wins, n)} ignoring non-WIN/LOSS resolutions."""
    out: dict[str, tuple[int, int]] = {}
    for label, signals in buckets.items():
        wins = 0
        n = 0
        for sig in signals:
            res = sig.get("resolution")
            if res == WIN_RESOLUTION:
                wins += 1
                n += 1
            elif res == LOSS_RESOLUTION:
                n += 1
        out[label] = (wins, n)
    return out


def _select_best(
    counts: dict[str, tuple[int, int]],
    wins_total: int,
    n_total: int,
    z: float,
) -> tuple[str, float, float, float] | None:
    """Find bucket with largest |delta|, tie-break by smaller n_b."""
    best: tuple[str, float, float, float] | None = None
    best_abs = -1.0
    best_n = 0
    for label, (wins_b, n_b) in counts.items():
        ci = compute_bucket_ci(wins_b, n_b, wins_total, n_total, z)
        if ci is None:
            continue
        delta, ci_lo, ci_hi = ci
        abs_delta = abs(delta)
        if abs_delta > best_abs or (abs_delta == best_abs and n_b < best_n):
            best = (label, delta, ci_lo, ci_hi)
            best_abs = abs_delta
            best_n = n_b
    return best
