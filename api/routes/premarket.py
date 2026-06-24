"""
api/routes/premarket.py
------------------------
Pre-market routine endpoints — one plan per trader per calendar date,
with any number of if-then scenarios per plan.

GET    /api/premarket                       - list lightweight day summaries in a date range
GET    /api/premarket/{date_str}            - fetch a plan by date (404 if not logged yet)
PUT    /api/premarket/{date_str}            - upsert a plan for a date (create or update)
POST   /api/premarket/{date_str}/scenarios  - add a scenario to a plan
PUT    /api/premarket/scenarios/{id}        - edit a scenario (incl. outcome quick-set)
GET    /api/premarket/scenarios/{id}        - fetch a single scenario
DELETE /api/premarket/scenarios/{id}        - delete a scenario
POST   /api/premarket/{date_str}/checkpoint - append a during-session checkpoint note
PUT    /api/premarket/{date_str}/review     - upsert the post-session review
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.db import get_db
from api.models_premarket import PlanReviewModel, PlanScenarioModel, PremarketPlanModel
from api.schemas_premarket import (
    CheckpointCreateRequest,
    PlanResponse,
    PlanUpsertRequest,
    PremarketDaySummary,
    ReviewResponse,
    ReviewUpsertRequest,
    ScenarioCreateRequest,
    ScenarioResponse,
    ScenarioUpdateRequest,
)
from api.services.premarket_helpers import (
    get_plan,
    get_scenario_for_user,
    parse_date,
    plan_to_response,
    scenario_to_response,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/premarket", response_model=list[PremarketDaySummary])
def list_plan_summaries(
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    date_from: Annotated[str, Query(alias="from")],
    date_to: Annotated[str, Query(alias="to")],
) -> list[PremarketDaySummary]:
    """Lightweight per-date summaries in [date_from, date_to] — powers the calendar grid indicator."""
    from_date = parse_date(date_from)
    to_date = parse_date(date_to)
    plans = db.scalars(
        select(PremarketPlanModel)
        .where(
            PremarketPlanModel.owner == current_user,
            PremarketPlanModel.date >= from_date,
            PremarketPlanModel.date <= to_date,
        )
        .order_by(PremarketPlanModel.date)
    ).all()
    scenario_counts = dict(
        db.execute(
            select(PlanScenarioModel.plan_id, func.count(PlanScenarioModel.id))
            .where(PlanScenarioModel.plan_id.in_([p.id for p in plans]))
            .group_by(PlanScenarioModel.plan_id)
        ).all()
    )
    return [
        PremarketDaySummary(
            date=p.date, daily_bias=p.daily_bias, scenario_count=scenario_counts.get(p.id, 0),
        )
        for p in plans
    ]


@router.get("/premarket/{date_str}", response_model=PlanResponse)
def get_plan_for_date(
    date_str: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlanResponse:
    """Fetch the pre-market plan for a specific date. Returns 404 if not logged yet."""
    target_date = parse_date(date_str)
    plan = get_plan(db, current_user, target_date)
    if plan is None:
        logger.warning("Premarket plan not found for user %s on %s", current_user, date_str)
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan_to_response(db, plan)


@router.put("/premarket/{date_str}", response_model=PlanResponse)
def upsert_plan(
    date_str: str,
    req: PlanUpsertRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlanResponse:
    """Create or update the pre-market plan for a specific date."""
    target_date = parse_date(date_str)
    now = datetime.now(timezone.utc)

    plan = get_plan(db, current_user, target_date)
    if plan is None:
        plan = PremarketPlanModel(
            id=str(uuid.uuid4()), owner=current_user, date=target_date,
            created_at=now, updated_at=now,
        )
        db.add(plan)
        logger.info("Premarket plan created for user %s on %s", current_user, date_str)
    else:
        plan.updated_at = now
        logger.info("Premarket plan updated for user %s on %s", current_user, date_str)

    plan.weekly_dealing_range = req.weekly_dealing_range
    plan.weekly_dol = req.weekly_dol
    plan.weekly_opening_gap = req.weekly_opening_gap
    plan.daily_bias = req.daily_bias
    plan.daily_bias_signals = req.daily_bias_signals
    plan.h4_pd_array = req.h4_pd_array
    plan.h4_pd_location = req.h4_pd_location
    plan.h1_zone = req.h1_zone
    plan.h1_structure = req.h1_structure
    plan.ltf_notes = req.ltf_notes
    plan.narrative = req.narrative

    db.commit()
    db.refresh(plan)
    return plan_to_response(db, plan)


@router.post("/premarket/{date_str}/scenarios", response_model=ScenarioResponse, status_code=201)
def create_scenario(
    date_str: str,
    req: ScenarioCreateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ScenarioResponse:
    """Add a scenario to a date's plan. No cap — a day can have any number of scenarios."""
    target_date = parse_date(date_str)
    plan = get_plan(db, current_user, target_date)
    if plan is None:
        logger.warning("Cannot add scenario - no plan for user %s on %s", current_user, date_str)
        raise HTTPException(status_code=404, detail="Plan not found - create the plan first")

    now = datetime.now(timezone.utc)
    scenario = PlanScenarioModel(
        id=str(uuid.uuid4()), plan_id=plan.id,
        reaction_setup_type=req.reaction_setup_type, reaction_setup_detail=req.reaction_setup_detail,
        target_level_type=req.target_level_type, target_level_detail=req.target_level_detail,
        notes=req.notes, created_at=now, updated_at=now,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    logger.info("Scenario created for user %s plan %s", current_user, plan.id)
    return scenario_to_response(scenario, plan.date)


@router.get("/premarket/scenarios/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ScenarioResponse:
    """Fetch a single scenario — used to show the linked scenario on a trade's detail page."""
    found = get_scenario_for_user(db, current_user, scenario_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    scenario, plan_date = found
    return scenario_to_response(scenario, plan_date)


@router.put("/premarket/scenarios/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: str,
    req: ScenarioUpdateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ScenarioResponse:
    """Edit a scenario, including the outcome quick-set."""
    found = get_scenario_for_user(db, current_user, scenario_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    scenario, plan_date = found

    scenario.reaction_setup_type = req.reaction_setup_type
    scenario.reaction_setup_detail = req.reaction_setup_detail
    scenario.target_level_type = req.target_level_type
    scenario.target_level_detail = req.target_level_detail
    scenario.notes = req.notes
    scenario.outcome_status = req.outcome_status
    scenario.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(scenario)
    logger.info("Scenario %s updated by user %s", scenario_id, current_user)
    return scenario_to_response(scenario, plan_date)


@router.delete("/premarket/scenarios/{scenario_id}", status_code=204)
def delete_scenario(
    scenario_id: str,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a scenario. Scoped to the current user via its parent plan's owner."""
    found = get_scenario_for_user(db, current_user, scenario_id)
    if found is None:
        logger.warning("Cannot delete scenario %s - not found for user %s", scenario_id, current_user)
        raise HTTPException(status_code=404, detail="Scenario not found")
    db.delete(found[0])
    db.commit()
    logger.info("Scenario %s deleted by user %s", scenario_id, current_user)


@router.post("/premarket/{date_str}/checkpoint", response_model=PlanResponse, status_code=201)
def add_checkpoint(
    date_str: str,
    req: CheckpointCreateRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> PlanResponse:
    """Append a during-session checkpoint note. Creates the plan row if it doesn't exist yet."""
    target_date = parse_date(date_str)
    now = datetime.now(timezone.utc)

    plan = get_plan(db, current_user, target_date)
    if plan is None:
        plan = PremarketPlanModel(
            id=str(uuid.uuid4()), owner=current_user, date=target_date,
            checkpoints=[], created_at=now, updated_at=now,
        )
        db.add(plan)

    plan.checkpoints = [*(plan.checkpoints or []), {"note": req.note, "timestamp": now.isoformat()}]
    plan.updated_at = now
    db.commit()
    db.refresh(plan)
    logger.info("Checkpoint added for user %s on %s", current_user, date_str)
    return plan_to_response(db, plan)


@router.put("/premarket/{date_str}/review", response_model=ReviewResponse)
def upsert_review(
    date_str: str,
    req: ReviewUpsertRequest,
    current_user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ReviewResponse:
    """Upsert the post-session review for a date's plan. 404s if no plan exists yet."""
    target_date = parse_date(date_str)
    plan = get_plan(db, current_user, target_date)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan not found - a review needs a plan first")

    now = datetime.now(timezone.utc)
    review = db.scalar(select(PlanReviewModel).where(PlanReviewModel.plan_id == plan.id))
    if review is None:
        review = PlanReviewModel(
            id=str(uuid.uuid4()), plan_id=plan.id, created_at=now, updated_at=now,
        )
        db.add(review)
    else:
        review.updated_at = now

    review.execution_grade = req.execution_grade
    db.commit()
    db.refresh(review)
    logger.info("Review upserted for user %s plan %s", current_user, plan.id)
    return ReviewResponse.model_validate(review)
