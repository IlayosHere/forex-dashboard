"""
api/routes/experiments.py
--------------------------
CRUD + evaluation endpoints for historical backtesting experiments.

POST /api/experiments/evaluate — ephemeral evaluate (no save)
GET  /api/experiments          — list saved experiments
POST /api/experiments          — create saved experiment
GET  /api/experiments/{id}     — single experiment
PUT  /api/experiments/{id}     — update experiment (clears last_summary)
DELETE /api/experiments/{id}   — delete
POST /api/experiments/{id}/run — re-evaluate saved experiment and cache result
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.experiments import evaluate_experiment
from api.auth import get_current_user
from api.db import get_db
from api.models_gates import ExperimentModel
from api.schemas_gates import (
    ExperimentCreateRequest,
    ExperimentEvaluateRequest,
    ExperimentResponse,
    ExperimentResultResponse,
    ExperimentUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.post("/evaluate", response_model=ExperimentResultResponse)
def evaluate_ephemeral(
    body: ExperimentEvaluateRequest,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExperimentResultResponse:
    """Evaluate conditions against historical signals without saving."""
    result = evaluate_experiment(
        db=db,
        strategy=body.strategy,
        conditions=[c.model_dump() for c in body.conditions],
        date_from=body.date_from,
        date_to=body.date_to,
    )
    return ExperimentResultResponse(**result)


@router.get("", response_model=list[ExperimentResponse])
def list_experiments(
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    strategy: str = Query(..., description="Strategy slug"),
) -> list[ExperimentResponse]:
    """List saved experiments for a strategy, newest first."""
    rows = db.scalars(
        select(ExperimentModel)
        .where(ExperimentModel.strategy == strategy)
        .order_by(ExperimentModel.created_at.desc())
    ).all()
    return [ExperimentResponse.model_validate(r) for r in rows]


@router.post("", response_model=ExperimentResponse, status_code=201)
def create_experiment(
    body: ExperimentCreateRequest,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExperimentResponse:
    """Save a new experiment definition."""
    now = datetime.now(timezone.utc)
    model = ExperimentModel(
        id=str(uuid4()),
        name=body.name,
        strategy=body.strategy,
        conditions=[c.model_dump() for c in body.conditions],
        date_from=body.date_from,
        date_to=body.date_to,
        notes=body.notes,
        created_at=now,
        updated_at=now,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return ExperimentResponse.model_validate(model)


@router.get("/{experiment_id}", response_model=ExperimentResponse)
def get_experiment(
    experiment_id: str,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExperimentResponse:
    """Fetch a single saved experiment."""
    model = db.get(ExperimentModel, experiment_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return ExperimentResponse.model_validate(model)


@router.put("/{experiment_id}", response_model=ExperimentResponse)
def update_experiment(
    experiment_id: str,
    body: ExperimentUpdateRequest,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExperimentResponse:
    """Update an experiment. Clears cached last_summary on condition change."""
    model = db.get(ExperimentModel, experiment_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    conditions_changed = body.conditions is not None
    if body.name is not None:
        model.name = body.name
    if body.conditions is not None:
        model.conditions = [c.model_dump() for c in body.conditions]
        model.last_summary = None
        model.last_run_at = None
    if body.date_from is not None:
        model.date_from = body.date_from
        model.last_summary = None
    if body.date_to is not None:
        model.date_to = body.date_to
        model.last_summary = None
    if body.notes is not None:
        model.notes = body.notes
    model.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(model)
    if conditions_changed:
        logger.info("Experiment '%s' updated — last_summary cleared", model.name)
    return ExperimentResponse.model_validate(model)


@router.delete("/{experiment_id}", status_code=204)
def delete_experiment(
    experiment_id: str,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a saved experiment."""
    model = db.get(ExperimentModel, experiment_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    db.delete(model)
    db.commit()


@router.post("/{experiment_id}/run", response_model=ExperimentResultResponse)
def run_experiment(
    experiment_id: str,
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExperimentResultResponse:
    """Re-evaluate a saved experiment against the current signal dataset."""
    model = db.get(ExperimentModel, experiment_id)
    if model is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    result = evaluate_experiment(
        db=db,
        strategy=model.strategy,
        conditions=model.conditions,
        date_from=model.date_from,
        date_to=model.date_to,
    )
    model.last_run_at = datetime.now(timezone.utc)
    model.last_summary = _summarize(result)
    db.commit()
    return ExperimentResultResponse(**result)


def _summarize(result: dict[str, Any]) -> dict[str, Any]:
    """Extract lightweight summary for caching on the model."""
    return {
        "passing_signals": result["passing_signals"],
        "win_rate_passed": result["win_rate_passed"],
        "win_rate_baseline": result["win_rate_baseline"],
        "delta_vs_baseline": result["delta_vs_baseline"],
    }
