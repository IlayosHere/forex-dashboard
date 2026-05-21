"""
api/models_gates.py
-------------------
SQLAlchemy models for the parameter-gating and experiment system.

  - GateSetModel: named, versioned condition sets that filter live signals
  - GradeThresholdsModel: per-strategy A/B/C/D score cutoffs
  - ExperimentModel: saved historical backtest definitions
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class GateSetModel(Base):
    """A named, versioned collection of AND-combined gate conditions for one strategy.

    Only one set may be ``is_active=True`` per strategy at a time.
    Older sets are retained for audit — deactivating does not delete them.
    """

    __tablename__ = "gate_sets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    owner: Mapped[str] = mapped_column(String, nullable=False, default="admin")
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    conditions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_gate_sets_owner_strategy", "owner", "strategy"),
        Index("ix_gate_sets_strategy_active", "strategy", "is_active"),
    )


class GradeThresholdsModel(Base):
    """Per-strategy cutoffs mapping normalized score to A/B/C/D grade.

    Normalized score = round(100 * raw_score / max_possible), clipped to [-100, 100].
    Grade assignment:
      A  — normalized >= a_min
      B  — normalized >= b_min
      C  — normalized >= 0
      D  — normalized < 0  (all confirmed edges working against the signal)
    """

    __tablename__ = "grade_thresholds"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    owner: Mapped[str] = mapped_column(String, nullable=False, default="admin")
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    a_min: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    b_min: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_grade_thresholds_strategy_active", "strategy", "is_active"),
    )


class ExperimentModel(Base):
    """A saved, named hypothesis: conditions + date range applied to historical signals.

    ``last_summary`` caches the most recent run result so the list page avoids
    re-evaluating every experiment on load.
    """

    __tablename__ = "experiments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    owner: Mapped[str] = mapped_column(String, nullable=False, default="admin")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    conditions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    date_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    date_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_experiments_owner_strategy", "owner", "strategy"),
    )
