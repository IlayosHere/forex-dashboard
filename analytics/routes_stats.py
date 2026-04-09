"""
analytics/routes_stats.py
-------------------------
FastAPI router for analytics statistics endpoints.

GET /api/analytics/univariate/{param_name} — per-parameter win-rate breakdown.
GET /api/analytics/summary                 — overall strategy analytics summary.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from analytics.enrichment import enrich_batch, fetch_resolved
from analytics.registry import get_param_def, get_params_for_strategy
from analytics.schemas import SummaryResponse, UnivariateReportResponse
from analytics.stats.report import build_summary, build_univariate_report
from api.auth import get_current_user
from api.db import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/univariate/{param_name}",
    response_model=UnivariateReportResponse,
)
def get_univariate_report(
    param_name: Annotated[str, Path(description="Registered parameter name")],
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    strategy: str = Query(..., description="Strategy slug (required)"),
) -> UnivariateReportResponse:
    """Return per-bucket win-rate analysis for a single parameter."""
    param_def = get_param_def(param_name)
    if param_def is None:
        logger.warning("Unknown param requested: %s", param_name)
        raise HTTPException(
            status_code=404,
            detail=f"Parameter '{param_name}' is not registered",
        )
    signals = fetch_resolved(db, strategy=strategy)
    enriched = enrich_batch(signals)
    report = build_univariate_report(
        param_name, param_def.dtype, strategy, enriched,
    )
    return UnivariateReportResponse(**report)


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    _user: Annotated[str, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    strategy: str = Query(..., description="Strategy slug (required)"),
) -> SummaryResponse:
    """Return overall analytics summary for a strategy."""
    signals = fetch_resolved(db, strategy=strategy)
    enriched = enrich_batch(signals)
    param_defs = [
        {"name": p.name, "dtype": p.dtype}
        for p in get_params_for_strategy(strategy)
    ]
    result = build_summary(strategy, enriched, param_defs)
    return SummaryResponse(**result)
