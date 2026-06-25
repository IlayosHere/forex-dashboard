"""
api/schemas.py
--------------
Pydantic v2 request/response models for the Forex Trade Journal API.

All models use ConfigDict(from_attributes=True) so they can be built directly
from SQLAlchemy ORM instances with model_validate().

Trade journal schemas live in api/schemas_trade.py and are re-exported here
for backward-compatible imports.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.schemas_mistake import (  # noqa: F401 -- re-export
    MistakeCreateRequest,
    MistakeResponse,
)
from api.schemas_stats import (  # noqa: F401 -- re-export
    DailySummaryPoint,
    EquityCurvePoint,
)
from api.schemas_trade import (  # noqa: F401 -- re-export
    TradeCreateRequest,
    TradeResponse,
    TradeStatsResponse,
    TradeUpdateRequest,
)


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

_VALID_ACCOUNT_TYPES = ("demo", "live", "funded", "backtest")
_VALID_INSTRUMENT_TYPES = ("forex", "futures", "futures_mnq", "futures_mes")
_VALID_ACCOUNT_STATUSES = ("active", "passed", "failed", "closed")


class AccountCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    model_config = ConfigDict(extra="forbid")

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
    model_config = ConfigDict()

    symbol: str
    entry: float
    sl_pips: float = Field(gt=0)
    account_balance: float
    risk_percent: float
    tp_pips: float | None = None
    instrument_type: str = "forex"


class CalculateResponse(BaseModel):
    model_config = ConfigDict()

    lot_size: float
    risk_usd: float
    sl_pips: float
    rr: float | None
    instrument_type: str = "forex"
    min_lot_applied: bool = False


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

class CalendarEventResponse(BaseModel):
    """Pydantic v2 response model for a single economic calendar event."""

    model_config = ConfigDict()

    id: str
    name: str
    currency: str
    datetime_utc: str
    datetime_et: str
    impact: str
    promoted: bool
    previous: str | None
    forecast: str | None
    actual: str | None
    beat_miss: str
    session_bucket: str


class MarketHolidayResponse(BaseModel):
    """Pydantic v2 response model for an NQ/CME Globex closure or thin-volume day."""

    model_config = ConfigDict()

    id: str
    date: str
    label: str
    closure_type: str
    early_close_et: str | None
    note: str | None
