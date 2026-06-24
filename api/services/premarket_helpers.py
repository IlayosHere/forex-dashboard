"""
api/services/premarket_helpers.py
-----------------------------------
Shared lookup/response-building helpers for the pre-market routine routes.
Extracted from api/routes/premarket.py to keep that file within size limits.
"""
from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.models_premarket import PlanReviewModel, PlanScenarioModel, PremarketPlanModel
from api.schemas_premarket import PlanResponse, ReviewResponse, ScenarioResponse


def parse_date(date_str: str) -> date:
    """Parse ISO date string YYYY-MM-DD, raise 422 on invalid format."""
    try:
        return date.fromisoformat(date_str)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid date format: {date_str!r}. Use YYYY-MM-DD",
        ) from exc


def get_plan(db: Session, owner: str, target_date: date) -> PremarketPlanModel | None:
    """Fetch a plan by owner+date, or None if not logged yet."""
    return db.scalar(
        select(PremarketPlanModel).where(
            PremarketPlanModel.owner == owner,
            PremarketPlanModel.date == target_date,
        )
    )


def scenario_to_response(scenario: PlanScenarioModel, plan_date: date) -> ScenarioResponse:
    """Build a ScenarioResponse, filling in the parent plan's date (not a column on the scenario).

    Built from explicit fields rather than model_validate(scenario) since `date` isn't a
    column on PlanScenarioModel and from_attributes has nowhere to read it from.
    """
    return ScenarioResponse(
        id=scenario.id,
        plan_id=scenario.plan_id,
        date=plan_date,
        reaction_setup_type=scenario.reaction_setup_type,
        reaction_setup_detail=scenario.reaction_setup_detail,
        target_level_type=scenario.target_level_type,
        target_level_detail=scenario.target_level_detail,
        notes=scenario.notes,
        outcome_status=scenario.outcome_status,
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
    )


def plan_to_response(db: Session, plan: PremarketPlanModel) -> PlanResponse:
    """Build a PlanResponse with scenarios explicitly loaded (relationship is lazy=noload)."""
    scenarios = db.scalars(
        select(PlanScenarioModel)
        .where(PlanScenarioModel.plan_id == plan.id)
        .order_by(PlanScenarioModel.created_at)
    ).all()
    review = db.scalar(select(PlanReviewModel).where(PlanReviewModel.plan_id == plan.id))
    resp = PlanResponse.model_validate(plan)
    resp.scenarios = [scenario_to_response(s, plan.date) for s in scenarios]
    resp.review = ReviewResponse.model_validate(review) if review is not None else None
    return resp


def get_scenario_for_user(
    db: Session, owner: str, scenario_id: str,
) -> tuple[PlanScenarioModel, date] | None:
    """Fetch a scenario + its parent plan's date, scoped to the current user."""
    row = db.execute(
        select(PlanScenarioModel, PremarketPlanModel.date)
        .join(PremarketPlanModel, PlanScenarioModel.plan_id == PremarketPlanModel.id)
        .where(PlanScenarioModel.id == scenario_id, PremarketPlanModel.owner == owner)
    ).first()
    return (row[0], row[1]) if row is not None else None
