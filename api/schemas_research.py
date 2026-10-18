"""
api/schemas_research.py
-----------------------
Pydantic v2 response and request models for the Research page.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

IdeaStatus = Literal["confirmed", "candidate", "parked", "killed"]
QueueKind = Literal["idea", "note"]
QueueStage = Literal["1", "2", "3", "any"]
QueueStatus = Literal["queued", "picked_up", "answered"]


class ResearchStatus(BaseModel):
    """The headline numbers: how many looks, what bar a new idea must clear, trials left."""

    looks: int
    promotion_bar: float
    log_entries: int
    trials_run: int
    trials_budget: int
    trials_left: int
    next_trial: int
    next_trial_alpha: float | None
    alpha_project_total: float | None
    pipeline_value: str | None


class Note(BaseModel):
    label: str
    text: str


class Edge(BaseModel):
    period: str
    value: str


class StageCard(BaseModel):
    key: str
    label: str
    strategy: str
    rule: str
    fires_on: str | None
    edges: list[Edge]
    planning_value: str | None


class Baseline(BaseModel):
    version: int
    adopted_on: str
    mechanism: str
    stages: list[StageCard]
    funded_rules: list[Note]
    challenger_rules: list[Note]


class IdeaResult(BaseModel):
    label: str
    market: str | None = None
    n: int | None = None
    hit: float | None = None
    control: float | None = None
    excess: float | None = None
    z: float | None = None


class Idea(BaseModel):
    id: str
    name: str
    stage: str
    status: IdeaStatus
    round: str | None = None
    rule: str
    plain: str
    notes: str | None = None
    years: str | None = None
    report: str
    log: list[int] = Field(default_factory=list)
    trials: list[int] = Field(default_factory=list)
    results: list[IdeaResult] = Field(default_factory=list)


class Trial(BaseModel):
    trial_no: int
    hypothesis_id: str
    period: str
    when: str
    n_trades: int | None
    hit_rate: float | None
    control_hit_rate: float | None
    z_vs_control: float | None
    z_decision: float | None
    excess_pts: float | None
    verdict: str
    alpha: float | None
    notes: str


class AlphaRow(BaseModel):
    trial: int
    alpha: float
    state: Literal["passed", "failed", "open"]


class LogEntry(BaseModel):
    n: int
    date: str
    idea: str
    looked_at: str
    variants: int
    result: str


class JourneyItem(BaseModel):
    date: str
    kind: Literal["decision", "trial", "exploration"]
    title: str
    detail: str


class QueueItem(BaseModel):
    id: str
    kind: QueueKind
    title: str
    stage: str
    about: str | None = None
    status: QueueStatus
    submitted_at: str
    submitted_by: str | None = None
    round: str | None = None
    answer: str | None = None
    body: str


class QueueCreate(BaseModel):
    """What the owner types into the Research page."""

    kind: QueueKind
    title: str = Field(min_length=3, max_length=120)
    stage: QueueStage = "any"
    about: str | None = Field(default=None, max_length=40)
    body: str = Field(min_length=10, max_length=4000)


class ResearchOverview(BaseModel):
    status: ResearchStatus
    baseline: Baseline | None
    ideas: list[Idea]
    trials: list[Trial]
    alpha_plan: list[AlphaRow]
    exploration_log: list[LogEntry]
    lessons: list[str]
    journey: list[JourneyItem]
    queue: list[QueueItem]
    warnings: list[str]
    source: str
    fetched_at: str


class ReportResponse(BaseModel):
    path: str
    text: str
