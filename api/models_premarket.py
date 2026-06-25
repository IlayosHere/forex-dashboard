"""
api/models_premarket.py
------------------------
SQLAlchemy 2.0 ORM models for the pre-market routine feature.

Split from api/models.py to stay under its 300-line limit (see docs/coding-standards.md).

Models:
  - PremarketPlanModel: one HTF->LTF plan per trader per calendar date
  - PlanScenarioModel: a primary/alternate if-then scenario within a plan
  - PlanReviewModel: post-session plan-vs-actual grading
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Date, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


class PremarketPlanModel(Base):
    """Pre-market HTF->LTF routine: one plan per trader per calendar date."""

    __tablename__ = "premarket_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    owner: Mapped[str] = mapped_column(String, nullable=False, default="admin")
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # HTF -> LTF ladder — every step independently nullable/skippable
    weekly_dealing_range: Mapped[str | None] = mapped_column(String, nullable=True)
    weekly_dol: Mapped[str | None] = mapped_column(String, nullable=True)
    weekly_opening_gap: Mapped[str | None] = mapped_column(String, nullable=True)
    daily_bias: Mapped[str | None] = mapped_column(String, nullable=True)
    daily_bias_signals: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    h4_pd_array: Mapped[str | None] = mapped_column(String, nullable=True)
    h4_pd_location: Mapped[str | None] = mapped_column(String, nullable=True)
    h1_zone: Mapped[str | None] = mapped_column(String, nullable=True)
    h1_structure: Mapped[str | None] = mapped_column(String, nullable=True)
    ltf_notes: Mapped[str | None] = mapped_column(String, nullable=True)

    narrative: Mapped[str] = mapped_column(String, nullable=False, default="")
    checkpoints: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    scenarios: Mapped[list[PlanScenarioModel]] = relationship(
        "PlanScenarioModel", back_populates="plan", lazy="noload", cascade="all, delete-orphan",
    )
    review: Mapped[PlanReviewModel | None] = relationship(
        "PlanReviewModel", back_populates="plan", lazy="noload",
        uselist=False, cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_premarket_plans_owner", "owner"),
        Index("ix_premarket_plans_owner_date", "owner", "date"),
        UniqueConstraint("owner", "date", name="uq_premarket_plan_owner_date"),
    )


class PlanScenarioModel(Base):
    """An if-then scenario within a pre-market plan — a day can have any number of these."""

    __tablename__ = "plan_scenarios"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    plan_id: Mapped[str] = mapped_column(
        String, ForeignKey("premarket_plans.id", ondelete="CASCADE"), nullable=False,
    )

    # The trade: area to take it from (same taxonomy as trade ict_setup_type/ict_setup_detail)
    # -> DOL traded into (external liquidity = a high/low, or internal liquidity = an FVG).
    reaction_setup_type: Mapped[str | None] = mapped_column(String, nullable=True)
    reaction_setup_detail: Mapped[str | None] = mapped_column(String, nullable=True)
    target_level_type: Mapped[str | None] = mapped_column(String, nullable=True)
    target_level_detail: Mapped[str | None] = mapped_column(String, nullable=True)

    # Free text — for whatever the structured fields above don't capture
    notes: Mapped[str] = mapped_column(String, nullable=False, default="")

    # Set manually at review time — never auto-derived from trade P&L
    outcome_status: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    plan: Mapped[PremarketPlanModel] = relationship(
        "PremarketPlanModel", back_populates="scenarios", lazy="noload",
    )

    __table_args__ = (
        Index("ix_plan_scenarios_plan_id", "plan_id"),
    )


class PlanReviewModel(Base):
    """Post-session grading for a pre-market plan.

    Execution is graded separately from outcome to avoid outcome bias.
    """

    __tablename__ = "plan_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    plan_id: Mapped[str] = mapped_column(
        String, ForeignKey("premarket_plans.id", ondelete="CASCADE"), nullable=False, unique=True,
    )
    bias_correct: Mapped[str | None] = mapped_column(String, nullable=True)
    execution_grade: Mapped[str | None] = mapped_column(String, nullable=True)
    emotion_tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    review_notes: Mapped[str] = mapped_column(String, nullable=False, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    plan: Mapped[PremarketPlanModel] = relationship(
        "PremarketPlanModel", back_populates="review", lazy="noload",
    )

    __table_args__ = (
        Index("ix_plan_reviews_plan_id", "plan_id"),
    )
