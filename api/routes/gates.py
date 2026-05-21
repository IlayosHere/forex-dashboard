"""
api/routes/gates.py
-------------------
CRUD endpoints for gate sets (parameter filters for live signals).

POST /api/gate-sets/preview — evaluate conditions without saving
GET  /api/gate-sets         — list gate sets per strategy
POST /api/gate-sets         — create new gate set (starts inactive)
GET  /api/gate-sets/{id}    — single gate set
PUT  /api/gate-sets/{id}    — update name/description/conditions
POST /api/gate-sets/{id}/activate — activate; deactivates all others for this strategy
DELETE /api/gate-sets/{id}  — delete
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.conditions import evaluate_all
from analytics.signal_enricher import ANALYTICS_PARAMS_KEY
from api.auth import get_current_user
from api.db import get_db
from api.models import SignalModel
from api.models_gates import GateSetModel
from api.schemas_gates import (
    GatePreviewRequest,
    GatePreviewResponse,
    GateSetCreateRequest,
    GateSetResponse,
    GateSetUpdateRequest,
)
from analytics.types import LOSS_RESOLUTION, WIN_RESOLUTION

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/gate-sets", tags=["gates"])


@router.post("/preview", response_model=GatePreviewResponse)
def preview_gate_set(
    body: GatePreviewRequest,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GatePreviewResponse:
    """Evaluate conditions against historical signals without saving."""
    conditions = [c.model_dump() for c in body.conditions]
    signals = _fetch_all_signals(db, body.strategy)
    return _compute_preview(signals, conditions)


@router.get("", response_model=list[GateSetResponse])
def list_gate_sets(
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    strategy: str = Query(..., description="Strategy slug"),
) -> list[GateSetResponse]:
    """List all gate sets for a strategy, active first."""
    rows = db.scalars(
        select(GateSetModel)
        .where(GateSetModel.strategy == strategy)
        .order_by(GateSetModel.is_active.desc(), GateSetModel.created_at.desc())
    ).all()
    return [GateSetResponse.model_validate(r) for r in rows]


@router.post("", response_model=GateSetResponse, status_code=201)
def create_gate_set(
    body: GateSetCreateRequest,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GateSetResponse:
    """Create a new gate set. Starts inactive — explicitly activate when ready."""
    now = datetime.now(timezone.utc)
    model = GateSetModel(
        id=str(uuid4()),
        strategy=body.strategy,
        name=body.name,
        description=body.description,
        is_active=False,
        conditions=[c.model_dump() for c in body.conditions],
        created_at=now,
        updated_at=now,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return GateSetResponse.model_validate(model)


@router.get("/{gate_set_id}", response_model=GateSetResponse)
def get_gate_set(
    gate_set_id: str,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GateSetResponse:
    """Fetch a single gate set by ID."""
    model = db.get(GateSetModel, gate_set_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Gate set not found")
    return GateSetResponse.model_validate(model)


@router.put("/{gate_set_id}", response_model=GateSetResponse)
def update_gate_set(
    gate_set_id: str,
    body: GateSetUpdateRequest,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GateSetResponse:
    """Update name, description, or conditions of an existing gate set."""
    model = db.get(GateSetModel, gate_set_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Gate set not found")
    if body.name is not None:
        model.name = body.name
    if body.description is not None:
        model.description = body.description
    if body.conditions is not None:
        model.conditions = [c.model_dump() for c in body.conditions]
    model.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(model)
    return GateSetResponse.model_validate(model)


@router.post("/{gate_set_id}/activate", response_model=GateSetResponse)
def activate_gate_set(
    gate_set_id: str,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GateSetResponse:
    """Activate a gate set, deactivating all others for the same strategy."""
    model = db.get(GateSetModel, gate_set_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Gate set not found")
    others = db.scalars(
        select(GateSetModel).where(
            GateSetModel.strategy == model.strategy,
            GateSetModel.id != gate_set_id,
            GateSetModel.is_active.is_(True),
        )
    ).all()
    for other in others:
        other.is_active = False
    model.is_active = True
    model.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(model)
    logger.info("Gate set '%s' activated for strategy=%s", model.name, model.strategy)
    return GateSetResponse.model_validate(model)


@router.delete("/{gate_set_id}", status_code=204)
def delete_gate_set(
    gate_set_id: str,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a gate set."""
    model = db.get(GateSetModel, gate_set_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Gate set not found")
    db.delete(model)
    db.commit()


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _fetch_all_signals(db: Session, strategy: str) -> list[SignalModel]:
    """Return all signals for a strategy (resolved and unresolved)."""
    return list(db.scalars(
        select(SignalModel).where(SignalModel.strategy == strategy)
    ).all())


def _compute_preview(
    signals: list[SignalModel],
    conditions: list[dict[str, Any]],
) -> GatePreviewResponse:
    """Evaluate conditions against signals and return summary stats."""
    failure_counts = [0] * len(conditions)
    pass_count = 0
    block_count = 0
    resolved_pass_wins = 0
    resolved_pass_n = 0
    resolved_base_wins = 0
    resolved_base_n = 0

    for sig in signals:
        params = (sig.signal_metadata or {}).get(ANALYTICS_PARAMS_KEY, {})
        passed, failed = evaluate_all(conditions, params)
        for idx in failed:
            failure_counts[idx] += 1
        if passed:
            pass_count += 1
        else:
            block_count += 1

        if sig.resolution in (WIN_RESOLUTION, LOSS_RESOLUTION):
            resolved_base_n += 1
            if sig.resolution == WIN_RESOLUTION:
                resolved_base_wins += 1
            if passed:
                resolved_pass_n += 1
                if sig.resolution == WIN_RESOLUTION:
                    resolved_pass_wins += 1

    total = pass_count + block_count
    pass_rate = pass_count / total if total > 0 else 0.0
    wr_passed = resolved_pass_wins / resolved_pass_n if resolved_pass_n > 0 else None
    wr_base = resolved_base_wins / resolved_base_n if resolved_base_n > 0 else 0.0
    delta = (wr_passed - wr_base) if wr_passed is not None else None

    return GatePreviewResponse(
        total_signals_evaluated=total,
        pass_count=pass_count,
        block_count=block_count,
        pass_rate=pass_rate,
        win_rate_passed=wr_passed,
        win_rate_baseline=wr_base if resolved_base_n > 0 else None,
        delta_vs_baseline=delta,
        per_condition_failure_count=failure_counts,
    )
