"""
api/routes/auto_gate.py
------------------------
POST /api/auto-gate/optimize         — run greedy gate optimizer
POST /api/auto-gate/recompute-grades — recompute A/B/C/D grades for all signals
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.candle_cache import CandleCache, get_app_cache
from analytics.confirmed_cache import get_confirmed_params
from analytics.enrichment import enrich_batch, fetch_resolved
from analytics.scoring import compute_score
from api.auth import get_current_user
from api.db import get_db
from api.models import SignalModel
from api.models_gates import GateSetModel, GradeThresholdsModel
from api.schemas_auto_gate import (
    OptimizeRequest,
    OptimizeResponse,
    RecomputeGradesRequest,
    RecomputeGradesResponse,
)
from api.services.gate_optimizer_runner import run_optimizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auto-gate", tags=["auto-gate"])

_AUTO_NAME_PREFIX = "Auto-optimized"
_A_MIN_DEFAULT = 60
_B_MIN_DEFAULT = 20


@router.post("/optimize", response_model=OptimizeResponse, status_code=200)
def optimize_gate(
    body: OptimizeRequest,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[CandleCache, Depends(get_app_cache)],
) -> OptimizeResponse:
    """Run the greedy gate optimizer for a strategy.

    When dry_run=False, creates and activates a new GateSet in the DB with
    the selected conditions. Returns full performance stats in both modes.
    """
    result = run_optimizer(db, body.strategy, cache, body.min_pass_rate)

    gate_set_id: str | None = None
    if not body.dry_run and result.get("conditions_selected"):
        gate_set_id = _create_and_activate(db, body.strategy, result["conditions_selected"])

    return OptimizeResponse(
        strategy=result["strategy"],
        conditions_selected=result["conditions_selected"],
        win_rate_baseline=result.get("win_rate_baseline"),
        win_rate_optimized=result.get("win_rate_optimized"),
        delta=result.get("delta"),
        pass_rate=result.get("pass_rate"),
        pass_count=result["pass_count"],
        total_signals=result["total_signals"],
        confirmed_params_found=result["confirmed_params_found"],
        dry_run=body.dry_run,
        gate_set_id=gate_set_id,
        reason=result.get("reason"),
    )


@router.post("/recompute-grades", response_model=RecomputeGradesResponse, status_code=200)
def recompute_grades(
    body: RecomputeGradesRequest,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    cache: Annotated[CandleCache, Depends(get_app_cache)],
) -> RecomputeGradesResponse:
    """Recompute A/B/C/D grades for all historical signals of a strategy."""
    thresholds = _get_or_create_thresholds(db, body.strategy)
    enriched = _load_enriched(db, body.strategy, cache)
    confirmed = get_confirmed_params(enriched, body.strategy)

    signals = list(db.scalars(
        select(SignalModel).where(SignalModel.strategy == body.strategy)
    ).all())

    recomputed = _apply_grades(db, signals, body.strategy, confirmed, thresholds)
    db.commit()

    logger.info(
        "Grade recompute via auto-gate: %d signals updated for strategy=%s",
        recomputed, body.strategy,
    )
    return RecomputeGradesResponse(strategy=body.strategy, recomputed=recomputed)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _create_and_activate(
    db: Session,
    strategy: str,
    conditions: list[dict[str, Any]],
) -> str:
    """Create a new GateSet and activate it, deactivating all prior active sets."""
    now = datetime.now(timezone.utc)
    gate_set_id = str(uuid4())

    for other in db.scalars(
        select(GateSetModel).where(
            GateSetModel.strategy == strategy,
            GateSetModel.is_active.is_(True),
        )
    ).all():
        other.is_active = False

    db.add(GateSetModel(
        id=gate_set_id,
        strategy=strategy,
        name=f"{_AUTO_NAME_PREFIX} {now.strftime('%Y-%m-%d')}",
        description="Created by auto-optimizer",
        is_active=True,
        conditions=conditions,
        created_at=now,
        updated_at=now,
    ))
    db.commit()
    logger.info("Auto-gate created and activated: id=%s strategy=%s", gate_set_id, strategy)
    return gate_set_id


def _get_or_create_thresholds(db: Session, strategy: str) -> GradeThresholdsModel:
    """Return active thresholds, creating defaults when none exist."""
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
        a_min=_A_MIN_DEFAULT,
        b_min=_B_MIN_DEFAULT,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def _load_enriched(db: Session, strategy: str, cache: CandleCache) -> list[dict]:
    """Fetch resolved signals and enrich them for confirmed-param lookup."""
    signals = fetch_resolved(db, strategy=strategy)
    if not signals:
        return []
    cache.warm(list({(s.symbol, s.strategy) for s in signals}))
    return enrich_batch(signals, candle_cache=cache)


def _apply_grades(
    db: Session,
    signals: list[SignalModel],
    strategy: str,
    confirmed: list[dict],
    thresholds: GradeThresholdsModel,
) -> int:
    """Recompute grade + score for each signal. Returns changed count."""
    changed = 0
    for sig in signals:
        result = compute_score(sig, strategy, candles=None, confirmed_params=confirmed)
        score = int(result["score"])
        max_possible = int(result["max_possible"])
        grade = _classify_grade(score, max_possible, thresholds.a_min, thresholds.b_min)
        if sig.grade != grade or sig.score_snapshot != score:
            sig.grade = grade
            sig.score_snapshot = score
            sig.score_max_snapshot = max_possible
            changed += 1
    return changed


def _classify_grade(score: int, max_possible: int, a_min: int, b_min: int) -> str | None:
    """Map normalized score to A/B/C/D grade letter."""
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
