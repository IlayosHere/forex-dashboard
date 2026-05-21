"""
runner/grade_runner.py
----------------------
Compute the A/B/C/D quality grade for a fresh signal at fire-time.

Grade is derived from the composite analytics score normalized to [-100, +100]
and classified against per-strategy thresholds stored in the DB.

  A — normalized score >= a_min  (strong alignment with confirmed edges)
  B — normalized score >= b_min
  C — normalized score >= 0
  D — normalized score < 0       (confirmed edges working against the signal)
  None — no confirmed params or no thresholds defined
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.confirmed_cache import get_confirmed_params
from analytics.scoring import compute_score
from analytics.signal_enricher import ANALYTICS_PARAMS_KEY
from api.models_gates import GradeThresholdsModel
from shared.signal import Signal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GradeDecision:
    """Result of grading a signal."""

    grade: str | None
    score: int | None
    max_possible: int | None
    thresholds_id: str | None
    failed_params: list[str] = field(default_factory=list)


def compute_grade_for_signal(
    db: Session,
    signal: Signal,
    enriched: list[dict[str, Any]],
) -> GradeDecision:
    """Compute A/B/C/D grade for *signal* using FDR-confirmed analytics params.

    Parameters
    ----------
    db :
        Active SQLAlchemy session — used to load grade thresholds.
    signal :
        Fresh signal whose metadata already contains ``_analytics_params``
        (i.e., ``compute_and_attach`` has already run).
    enriched :
        Pre-computed enriched historical signals for this strategy. Passed to
        the confirmed-params cache; only re-computed if the cache has expired.
    """
    thresholds = _get_thresholds(db, signal.strategy)
    confirmed = get_confirmed_params(enriched, signal.strategy)

    if not confirmed:
        return GradeDecision(None, None, None, thresholds.id if thresholds else None)

    result = compute_score(signal, signal.strategy, candles=None, confirmed_params=confirmed)
    score = int(result["score"])
    max_possible = int(result["max_possible"])

    if max_possible == 0 or thresholds is None:
        return GradeDecision(None, score, max_possible, thresholds.id if thresholds else None)

    normalized = _normalize(score, max_possible)
    grade = _classify(normalized, thresholds.a_min, thresholds.b_min)
    return GradeDecision(grade, score, max_possible, thresholds.id)


def _get_thresholds(db: Session, strategy: str) -> GradeThresholdsModel | None:
    """Return the active thresholds for a strategy, or None if unset."""
    return db.scalar(
        select(GradeThresholdsModel).where(
            GradeThresholdsModel.strategy == strategy,
            GradeThresholdsModel.is_active.is_(True),
        ),
    )


def _normalize(score: int, max_possible: int) -> int:
    """Map raw score to [-100, +100]."""
    return max(-100, min(100, round(100 * score / max_possible)))


def _classify(normalized: int, a_min: int, b_min: int) -> str:
    """Assign A/B/C/D from normalized score."""
    if normalized >= a_min:
        return "A"
    if normalized >= b_min:
        return "B"
    if normalized >= 0:
        return "C"
    return "D"
