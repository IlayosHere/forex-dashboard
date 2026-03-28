"""
api/schemas.py
--------------
Pydantic v2 request/response models for the Forex Signal Dashboard API.

All models use ConfigDict(from_attributes=True) so they can be built directly
from SQLAlchemy ORM instances with model_validate().
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SignalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    strategy: str
    symbol: str
    direction: str
    candle_time: datetime
    entry: float
    sl: float
    tp: float
    lot_size: float
    risk_pips: float
    spread_pips: float
    # DB column is signal_metadata; expose as metadata in JSON
    metadata: dict = Field(validation_alias="signal_metadata")
    created_at: datetime

    @field_validator("candle_time", "created_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


class SignalListResponse(BaseModel):
    items: list[SignalResponse]
    total: int


class CalculateRequest(BaseModel):
    symbol: str
    entry: float
    sl_pips: float
    account_balance: float
    risk_percent: float
    tp_pips: float | None = None
    instrument_type: str = "forex"


class CalculateResponse(BaseModel):
    lot_size: float
    risk_usd: float
    sl_pips: float
    rr: float | None
    instrument_type: str = "forex"


# ---------------------------------------------------------------------------
# Trade Journal
# ---------------------------------------------------------------------------


class TradeCreateRequest(BaseModel):
    signal_id: str | None = None
    strategy: str
    symbol: str
    instrument_type: str = "forex"
    direction: str
    entry_price: float
    sl_price: float
    tp_price: float | None = None
    lot_size: float
    risk_pips: float
    open_time: datetime
    tags: list[str] = []
    notes: str = ""
    rating: int | None = Field(default=None, ge=1, le=5)
    confidence: int | None = Field(default=None, ge=1, le=5)
    screenshot_url: str | None = None
    metadata: dict = {}

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in ("BUY", "SELL"):
            raise ValueError("direction must be BUY or SELL")
        return v


class TradeUpdateRequest(BaseModel):
    instrument_type: str | None = None
    exit_price: float | None = None
    sl_price: float | None = None
    tp_price: float | None = None
    lot_size: float | None = None
    status: str | None = None
    outcome: str | None = None
    close_time: datetime | None = None
    tags: list[str] | None = None
    notes: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    confidence: int | None = Field(default=None, ge=1, le=5)
    screenshot_url: str | None = None
    metadata: dict | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in ("open", "closed", "breakeven", "cancelled"):
            raise ValueError("status must be open, closed, breakeven, or cancelled")
        return v

    @field_validator("outcome")
    @classmethod
    def validate_outcome(cls, v: str | None) -> str | None:
        if v is not None and v not in ("win", "loss", "breakeven"):
            raise ValueError("outcome must be win, loss, or breakeven")
        return v


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    signal_id: str | None
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
    by_strategy: dict[str, dict]
    by_symbol: dict[str, dict]
