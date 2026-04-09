"""
api/schemas_trade.py
--------------------
Pydantic v2 request/response models for the trade journal endpoints.

Split from api/schemas.py to keep each module under the 200-line limit.
"""
from __future__ import annotations

from datetime import datetime, timezone

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TradeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str | None = None
    account_id: str | None = None
    strategy: str
    symbol: str
    instrument_type: str = "forex"
    direction: str
    entry_price: float = Field(gt=0)
    sl_price: float = Field(gt=0)
    tp_price: float | None = None
    lot_size: float = Field(gt=0)
    risk_pips: float | None = Field(default=None, gt=0)
    open_time: datetime
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    rating: int | None = Field(default=None, ge=1, le=5)
    confidence: int | None = Field(default=None, ge=1, le=5)
    screenshot_url: str | None = None
    metadata: dict = Field(default_factory=dict)

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        """Ensure direction is BUY or SELL."""
        if v not in ("BUY", "SELL"):
            raise ValueError("direction must be BUY or SELL")
        return v

    @field_validator("instrument_type")
    @classmethod
    def validate_instrument_type(cls, v: str) -> str:
        """Ensure instrument_type is forex or futures_mnq."""
        if v not in ("forex", "futures_mnq"):
            raise ValueError("instrument_type must be forex or futures_mnq")
        return v


class TradeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    instrument_type: str | None = None
    direction: str | None = None
    entry_price: float | None = Field(default=None, gt=0)
    exit_price: float | None = Field(default=None, gt=0)
    sl_price: float | None = Field(default=None, gt=0)
    tp_price: float | None = None
    lot_size: float | None = Field(default=None, gt=0)
    risk_pips: float | None = Field(default=None, gt=0)
    status: str | None = None
    outcome: str | None = None
    close_time: datetime | None = None
    tags: list[str] | None = None
    notes: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    confidence: int | None = Field(default=None, ge=1, le=5)
    screenshot_url: str | None = None
    metadata: dict | None = None

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str | None) -> str | None:
        """Ensure direction is BUY or SELL when provided."""
        if v is not None and v not in ("BUY", "SELL"):
            raise ValueError("direction must be BUY or SELL")
        return v

    @field_validator("instrument_type")
    @classmethod
    def validate_instrument_type(cls, v: str | None) -> str | None:
        """Ensure instrument_type is forex or futures_mnq when provided."""
        if v is not None and v not in ("forex", "futures_mnq"):
            raise ValueError("instrument_type must be forex or futures_mnq")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Ensure status is a valid trade status when provided."""
        if v is not None and v not in ("open", "closed", "breakeven", "cancelled"):
            raise ValueError("status must be open, closed, breakeven, or cancelled")
        return v

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, v: str | None) -> str | None:
        """Ensure outcome is a valid trade outcome when provided."""
        if v is not None and v not in ("win", "loss", "breakeven"):
            raise ValueError("outcome must be win, loss, or breakeven")
        return v


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    signal_id: str | None
    account_id: str | None = None
    account_name: str | None = None
    strategy: str
    symbol: str
    instrument_type: str
    direction: str
    entry_price: float
    exit_price: float | None
    sl_price: float
    tp_price: float | None
    lot_size: float
    status: str
    outcome: str | None
    pnl_pips: float | None
    pnl_usd: float | None
    rr_achieved: float | None
    risk_pips: float
    open_time: datetime
    close_time: datetime | None
    tags: list[str]
    notes: str
    rating: int | None
    confidence: int | None
    screenshot_url: str | None
    metadata: dict = Field(validation_alias="trade_metadata")
    created_at: datetime
    updated_at: datetime

    @field_validator("open_time", "close_time", "created_at", "updated_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class TradeStatsResponse(BaseModel):
    total_trades: int
    open_trades: int
    closed_trades: int
    wins: int
    losses: int
    breakevens: int
    win_rate: float | None
    avg_rr: float | None
    total_pnl_pips: float
    total_pnl_usd: float
    best_trade_pnl: float | None
    worst_trade_pnl: float | None
    current_streak: int
    profit_factor: float | None
    avg_hold_time_hours: float | None
    avg_win_pips: float | None = None
    avg_loss_pips: float | None = None
    avg_win_usd: float | None = None
    avg_loss_usd: float | None = None
    expectancy_usd: float | None = None
    expectancy_pips: float | None = None
    consistency_ratio: float | None = None
    by_strategy: dict[str, dict[str, Any]]
    by_symbol: dict[str, dict[str, Any]]
    by_account: dict[str, dict[str, Any]]
    by_day_of_week: dict[str, dict[str, Any]] = {}
    by_session: dict[str, dict[str, Any]] = {}
    by_confidence: dict[str, dict[str, Any]] = {}
    by_rating: dict[str, dict[str, Any]] = {}
