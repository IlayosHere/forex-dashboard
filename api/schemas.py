"""
api/schemas.py
--------------
Pydantic v2 request/response models for the Forex Signal Dashboard API.

All models use ConfigDict(from_attributes=True) so they can be built directly
from SQLAlchemy ORM instances with model_validate().

Trade journal schemas live in api/schemas_trade.py and are re-exported here
for backward-compatible imports.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.schemas_trade import (  # noqa: F401 -- re-export
    TradeCreateRequest,
    TradeResponse,
    TradeStatsResponse,
    TradeUpdateRequest,
)


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


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

_VALID_ACCOUNT_TYPES = ("demo", "live", "funded")
_VALID_INSTRUMENT_TYPES = ("forex", "futures_mnq")
_VALID_ACCOUNT_STATUSES = ("active", "passed", "failed", "closed")


class AccountCreateRequest(BaseModel):
    name: str
    account_type: str
    instrument_type: str
    status: str = "active"
    prop_firm: str | None = None
    phase: str | None = None
    balance: float | None = None

    @field_validator("account_type")
    @classmethod
    def validate_account_type(cls, v: str) -> str:
        if v not in _VALID_ACCOUNT_TYPES:
            raise ValueError(f"account_type must be one of {_VALID_ACCOUNT_TYPES}")
        return v

    @field_validator("instrument_type")
    @classmethod
    def validate_instrument_type(cls, v: str) -> str:
        if v not in _VALID_INSTRUMENT_TYPES:
            raise ValueError(f"instrument_type must be one of {_VALID_INSTRUMENT_TYPES}")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in _VALID_ACCOUNT_STATUSES:
            raise ValueError(f"status must be one of {_VALID_ACCOUNT_STATUSES}")
        return v


class AccountUpdateRequest(BaseModel):
    name: str | None = None
    status: str | None = None
    prop_firm: str | None = None
    phase: str | None = None
    balance: float | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        if v is not None and v not in _VALID_ACCOUNT_STATUSES:
            raise ValueError(f"status must be one of {_VALID_ACCOUNT_STATUSES}")
        return v


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    account_type: str
    instrument_type: str
    status: str
    prop_firm: str | None
    phase: str | None
    balance: float | None
    created_at: datetime

    @field_validator("created_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


# ---------------------------------------------------------------------------
# Calculator
# ---------------------------------------------------------------------------

class CalculateRequest(BaseModel):
    symbol: str
    entry: float
    sl_pips: float = Field(gt=0)
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
