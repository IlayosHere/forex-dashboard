"""
api/routes/research.py
----------------------
Research page endpoints. Everything is read from the prop-pipeline repo.

GET  /api/research          - the whole page: status, baseline, ideas, trials, journey, queue
GET  /api/research/report   - one report as markdown (?path=results/phase3/TRIAL7_REPORT.md)
GET  /api/research/queue    - the owner's idea queue
POST /api/research/queue    - add an idea or a note (201)
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from api.auth import get_current_user
from api.schemas_research import QueueCreate, QueueItem, ReportResponse, ResearchOverview
from api.services.research.overview import build_overview, idea_ids
from api.services.research.queue import QueueInputError, check_rate, create_item, list_items
from api.services.research.reports import read_report
from api.services.research.source import (
    Source,
    SourceError,
    SourceNotConfigured,
    SourceNotFound,
    get_source,
)

logger = logging.getLogger(__name__)

# Login is checked first, before the research source is even built.
router = APIRouter(prefix="/research", tags=["research"], dependencies=[Depends(get_current_user)])


def get_research_source() -> Source:
    """FastAPI dependency: the configured research source, or 503 if none is set up."""
    try:
        return get_source()
    except SourceNotConfigured as exc:
        logger.warning("Research source not configured: %s", exc)
        raise HTTPException(status_code=503, detail="Research source is not configured") from exc


SourceDep = Annotated[Source, Depends(get_research_source)]
UserDep = Annotated[str, Depends(get_current_user)]


@router.get("", response_model=ResearchOverview)
def get_research(source: SourceDep) -> dict:
    """Read every research file and return the page payload."""
    return build_overview(source)


@router.get("/report", response_model=ReportResponse)
def get_report(source: SourceDep, path: Annotated[str, Query(max_length=200)]) -> dict:
    """Fetch one report as markdown."""
    try:
        return {"path": path, "text": read_report(source, path)}
    except SourceNotFound as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc
    except SourceError as exc:
        logger.warning("Report %s refused: %s", path, exc)
        raise HTTPException(status_code=400, detail="Not a report path") from exc


@router.get("/queue", response_model=list[QueueItem])
def get_queue(source: SourceDep) -> list[dict]:
    """List the idea queue, newest first."""
    try:
        return list_items(source)[0]
    except SourceError as exc:
        raise HTTPException(status_code=502, detail="Queue could not be read") from exc


@router.post("/queue", response_model=QueueItem, status_code=201)
def add_queue_item(payload: QueueCreate, user: UserDep, source: SourceDep) -> dict:
    """Add an idea or a note to the queue for the next research round."""
    if not check_rate(user):
        raise HTTPException(status_code=429, detail="Too many submissions, try again later")
    try:
        ids = idea_ids(source)
        return create_item(source, payload.model_dump(), user, ids, datetime.now(timezone.utc))
    except QueueInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except SourceError as exc:
        logger.error("Queue write failed: %s", exc)
        raise HTTPException(status_code=502, detail="Could not save to the research repo") from exc
