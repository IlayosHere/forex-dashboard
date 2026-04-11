"""
analytics/stats/univariate.py
-----------------------------
Statistical analysis functions: win rates, confidence intervals,
chi-squared tests, and point-biserial correlation.
"""
from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from scipy.stats import chi2_contingency, pointbiserialr

from analytics.types import LOSS_RESOLUTION, WIN_RESOLUTION

logger = logging.getLogger(__name__)


@dataclass
class BucketWinRate:
    """Win-rate statistics for a single bucket of signals."""

    bucket_label: str
    wins: int
    losses: int
    total: int
    win_rate: float
    ci_lower: float
    ci_upper: float

    def as_dict(self) -> dict[str, Any]:
        """Serialize to plain dict."""
        return asdict(self)


def win_rate_by_bucket(
    buckets: dict[str, list[dict[str, Any]]],
) -> list[BucketWinRate]:
    """Compute win rate with Wilson CI for each bucket.

    Parameters
    ----------
    buckets : dict
        Mapping of bucket label to list of enriched signal dicts.

    Returns
    -------
    list[BucketWinRate] sorted by bucket label.
    """
    results: list[BucketWinRate] = []
    for label in sorted(buckets):
        signals = buckets[label]
        wins, losses = _count_outcomes(signals)
        total = wins + losses
        rate = wins / total if total > 0 else 0.0
        ci_lo, ci_hi = _wilson_ci(wins, total)
        results.append(BucketWinRate(
            bucket_label=label,
            wins=wins,
            losses=losses,
            total=total,
            win_rate=rate,
            ci_lower=ci_lo,
            ci_upper=ci_hi,
        ))
    return results


def chi_squared_test(
    buckets: dict[str, list[dict[str, Any]]],
) -> tuple[float, float] | None:
    """Run chi-squared test on win/loss counts across buckets.

    Returns
    -------
    (chi2_statistic, p_value) or None if fewer than 2 non-empty buckets.
    """
    labels = sorted(buckets)
    if len(labels) < 2:
        return None

    wins_row: list[int] = []
    losses_row: list[int] = []
    for label in labels:
        w, l = _count_outcomes(buckets[label])
        wins_row.append(w)
        losses_row.append(l)

    table = np.array([wins_row, losses_row])
    if table.sum() == 0:
        return None

    try:
        chi2, p_val, _, _ = chi2_contingency(table)
    except ValueError:
        logger.debug("chi2_contingency failed — likely degenerate table")
        return None

    return (float(chi2), float(p_val))


def two_proportion_ci(
    wins_a: int,
    n_a: int,
    wins_b: int,
    n_b: int,
    z: float = 1.96,
) -> tuple[float, float, float] | None:
    """Two-proportion z-test confidence interval for (p_a - p_b).

    Uses the unpooled standard error:

        p_a    = wins_a / n_a
        p_b    = wins_b / n_b
        delta  = p_a - p_b
        SE     = sqrt( p_a*(1-p_a)/n_a + p_b*(1-p_b)/n_b )
        ci_lo  = delta - z * SE
        ci_hi  = delta + z * SE

    Parameters
    ----------
    wins_a : int
        Wins in group A.
    n_a : int
        Total signals in group A.
    wins_b : int
        Wins in group B.
    n_b : int
        Total signals in group B.
    z : float
        Critical value (default 1.96 for 95% CI).

    Returns
    -------
    (delta, ci_lo, ci_hi) or None if either ``n_a`` or ``n_b`` is zero.
    """
    if n_a <= 0 or n_b <= 0:
        return None
    p_a = wins_a / n_a
    p_b = wins_b / n_b
    delta = p_a - p_b
    se = math.sqrt(p_a * (1 - p_a) / n_a + p_b * (1 - p_b) / n_b)
    return (delta, delta - z * se, delta + z * se)


def point_biserial_test(
    enriched: list[dict[str, Any]],
    param_name: str,
) -> tuple[float, float] | None:
    """Point-biserial correlation between a numeric param and outcome.

    Parameters
    ----------
    enriched : list[dict]
        Enriched signal dicts.
    param_name : str
        Key inside ``params`` to correlate.

    Returns
    -------
    (correlation, p_value) or None if fewer than 10 usable signals.
    """
    values: list[float] = []
    outcomes: list[int] = []
    for sig in enriched:
        val = sig.get("params", {}).get(param_name)
        res = sig.get("resolution")
        if val is None or res not in (WIN_RESOLUTION, LOSS_RESOLUTION):
            continue
        values.append(float(val))
        outcomes.append(1 if res == WIN_RESOLUTION else 0)

    if len(values) < 10:
        return None

    if len(set(outcomes)) < 2 or len(set(values)) < 2:
        return None

    try:
        corr, p_val = pointbiserialr(outcomes, values)
    except ValueError:
        logger.debug("pointbiserialr failed for param=%s", param_name)
        return None

    return (float(corr), float(p_val))


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _wilson_ci(
    wins: int,
    total: int,
    z: float = 1.96,
) -> tuple[float, float]:
    """Wilson score confidence interval for a binomial proportion."""
    if total == 0:
        return (0.0, 0.0)
    p = wins / total
    denom = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / denom
    margin = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


def _count_outcomes(
    signals: list[dict[str, Any]],
) -> tuple[int, int]:
    """Count (wins, losses) in a list of enriched signals."""
    wins = sum(1 for s in signals if s.get("resolution") == WIN_RESOLUTION)
    losses = sum(1 for s in signals if s.get("resolution") == LOSS_RESOLUTION)
    return wins, losses
