"""
api/schemas_stats.py
--------------------
Pydantic v2 response models for the extended statistics endpoints.

Split from schemas_trade.py to keep each module under the 200-line limit.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class EquityCurvePoint(BaseModel):
    """Single point on the equity curve."""

    date: str | None
    close_time: str | None
    pnl_usd: float
    pnl_pips: float
    cumulative_pnl_usd: float
    cumulative_pnl_pips: float
    trade_count: int
    outcome: str | None


class DailySummaryPoint(BaseModel):
    """Daily aggregated stats for calendar heatmap."""

    date: str
    trades: int
    wins: int
    losses: int
    breakevens: int
    pnl_usd: float
    pnl_pips: float
