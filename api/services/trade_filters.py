"""
api/services/trade_filters.py
------------------------------
FastAPI dependency classes for trade list and stats filter query parameters.
Extracted from api/routes/trades.py to keep the route file within size limits.
"""
from __future__ import annotations

from datetime import date

from fastapi import Query


class TradeFilterParams:
    """Dependency that collects trade filter query parameters."""

    def __init__(
        self,
        strategy: str | None = Query(default=None),
        symbol: str | None = Query(default=None),
        status: str | None = Query(default=None),
        outcome: str | None = Query(default=None),
        instrument_type: str | None = Query(default=None),
        account_id: str | None = Query(default=None),
        rule_followed: bool | None = Query(default=None),
        date_from: date | None = Query(default=None, alias="from"),
        date_to: date | None = Query(default=None, alias="to"),
    ) -> None:
        self.strategy = strategy
        self.symbol = symbol
        self.status = status
        self.outcome = outcome
        self.instrument_type = instrument_type
        self.account_id = account_id
        self.rule_followed = rule_followed
        self.date_from = date_from
        self.date_to = date_to


class StatsFilterParams:
    """Dependency for stats endpoints — excludes status/outcome filters."""

    def __init__(
        self,
        strategy: str | None = Query(default=None),
        symbol: str | None = Query(default=None),
        instrument_type: str | None = Query(default=None),
        account_id: str | None = Query(default=None),
        date_from: date | None = Query(default=None, alias="from"),
        date_to: date | None = Query(default=None, alias="to"),
    ) -> None:
        self.strategy = strategy
        self.symbol = symbol
        self.instrument_type = instrument_type
        self.account_id = account_id
        self.date_from = date_from
        self.date_to = date_to
