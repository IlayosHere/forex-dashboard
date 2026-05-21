"""
api/routes/grades.py
--------------------
GET /api/grade-thresholds?strategy=   — fetch active thresholds
PUT /api/grade-thresholds             — update thresholds (upsert)
POST /api/grade-thresholds/recompute  — retroactively regrade historical signals
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.candle_cache import CandleCache, get_app_cache
from analytics.confirmed_cache import get_confirmed_params, invalidate
from analytics.enrichment import enrich_batch, fetch_resolved
from analytics.scoring import compute_score
from api.auth import get_current_user
from api.db import get_db
from api.models import SignalModel
from api.models_gates import GradeThresholdsModel
from api.schemas_gates import (
    GradeRecomputeRequest,
    GradeRecomputeResponse,
    GradeThresholdsResponse,
    GradeThresholdsUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/grade-thresholds", tags=["grades"])


@router.get("", response_model=GradeThresholdsResponse)
def get_grade_thresholds(
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    strategy: str = Query(..., description="Strategy slug"),
) -> GradeThresholdsResponse:
    """Return active grade thresholds for a strategy, creating defaults if absent."""
    model = _get_or_create_thresholds(db, strategy)
    return GradeThresholdsResponse.model_validate(model)


@router.put("", response_model=GradeThresholdsResponse)
def update_grade_thresholds(
    body: GradeThresholdsUpdateRequest,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    strategy: str = Query(..., description="Strategy slug"),
) -> GradeThresholdsResponse:
    """Update A and B score thresholds for a strategy."""
    model = _get_or_create_thresholds(db, strategy)
    model.a_min = body.a_min
    model.b_min = body.b_min
    db.commit()
    db.refresh(model)
    invalidate(strategy)
    logger.info(
        "Grade thresholds updated for strategy=%s: A>=%d, B>=%d",
        strategy, body.a_min, body.b_min,
    )
    return GradeThresholdsResponse.model_validate(model)


@router.post("/recompute", response_model=GradeRecomputeResponse)
def recompute_grades(
    body: GradeRecomputeRequest,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[CandleCache, Depends(get_app_cache)],
) -> GradeRecomputeResponse:
    """Retroactively regrade all historical signals for a strategy.

    When dry_run=True, returns the count that would change without committing.
    """
    thresholds = _get_or_create_thresholds(db, body.strategy)
    enriched = _load_enriched(db, body.strategy, cache)  # noqa: F841 used for confirmed
    confirmed = get_confirmed_params(enriched, body.strategy)

    signals = list(db.scalars(
        select(SignalModel).where(SignalModel.strategy == body.strategy)
    ).all())

    recomputed = 0
    for sig in signals:
        result = compute_score(sig, body.strategy, candles=None, confirmed_params=confirmed)
        score = int(result["score"])
        max_possible = int(result["max_possible"])
        grade = _classify(score, max_possible, thresholds.a_min, thresholds.b_min)
        if sig.grade != grade or sig.score_snapshot != score:
            if not body.dry_run:
                sig.grade = grade
                sig.score_snapshot = score
                sig.score_max_snapshot = max_possible
            recomputed += 1

    if not body.dry_run:
        db.commit()
        logger.info(
            "Grade recompute: updated %d signals for strategy=%s",
            recomputed, body.strategy,
        )
    return GradeRecomputeResponse(
        strategy=body.strategy,
        dry_run=body.dry_run,
        recomputed=recomputed,
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_or_create_thresholds(db: Session, strategy: str) -> GradeThresholdsModel:
    """Return active thresholds; create defaults if none exist."""
    model = db.scalar(
        select(GradeThresholdsModel).where(
            GradeThresholdsModel.strategy == strategy,
            GradeThresholdsModel.is_active.is_(True),
        )
    )
    if model is not None:
        return model
    model = GradeThresholdsModel(
        id=str(uuid4()),
        strategy=strategy,
        a_min=60,
        b_min=20,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def _load_enriched(db: Session, strategy: str, cache: CandleCache) -> list[dict]:
    """Fetch and enrich resolved signals for the confirmed-params cache."""
    signals = fetch_resolved(db, strategy=strategy)
    if not signals:
        return []
    cache.warm(list({(s.symbol, s.strategy) for s in signals}))
    return enrich_batch(signals, candle_cache=cache)


def _classify(score: int, max_possible: int, a_min: int, b_min: int) -> str | None:
    """Assign A/B/C/D from raw score and thresholds."""
    if max_possible == 0:
        return None
    normalized = max(-100, min(100, round(100 * score / max_possible)))
    if normalized >= a_min:
        return "A"
    if normalized >= b_min:
        return "B"
    if normalized >= 0:
        return "C"
    return "D"
