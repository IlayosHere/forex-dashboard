"""
api/schemas_trade.py
--------------------
Pydantic v2 request/response models for the trade journal endpoints.

Split from api/schemas.py to keep each module under the 200-line limit.
"""
from __future__ import annotations

from datetime import datetime, timezone

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LinkedMistake(BaseModel):
    """A mistake vocabulary entry linked to a trade."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str

from shared.feelings import FEELING_VALUES
from shared.ict_taxonomy import (
    HTF_BIAS_VALUES,
    IFVG_TIMEFRAMES,
    SETUP_DETAIL_MAP,
    SETUP_TYPES,
    TP_TARGETS,
)
from shared.qt_taxonomy import QT_ENTRY_TYPES, QT_FVG_TYPES, QT_QUARTERS, QT_TP_TARGETS


def _validate_feeling(v: str | None) -> str | None:
    """Validate that a feeling value belongs to the known enum."""
    if v is not None and v not in FEELING_VALUES:
        raise ValueError(f"feeling must be one of {FEELING_VALUES}")
    return v


def _validate_ict_detail_for_type(
    setup_type: str | None, setup_detail: str | None,
) -> None:
    """Cross-validate that ict_setup_detail belongs to ict_setup_type's allowed list."""
    if setup_type is None or setup_detail is None:
        return
    allowed = SETUP_DETAIL_MAP.get(setup_type, [])
    if allowed and setup_detail not in allowed:
        raise ValueError(
            f"ict_setup_detail '{setup_detail}' is not valid for "
            f"ict_setup_type '{setup_type}'. Must be one of {allowed}",
        )


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
    metadata: dict[str, Any] = Field(default_factory=dict)

    # ICT params — required when instrument_type is futures_mnq
    ict_setup_type: str | None = None
    ict_setup_detail: str | None = None
    ict_tp_target: str | None = None
    ict_ifvg_timeframe: str | None = None
    ict_ifvg_bars: int | None = Field(default=None, ge=1, le=100)
    ict_smt_present: bool | None = None
    ict_tdo_aligned: bool | None = None
    ict_htf_bias: str | None = None
    fees: float | None = Field(default=None, ge=0)
    criteria_met_at_entry: bool | None = None

    # Emotional state (MNQ only in practice)
    feeling_before: str | None = None
    feeling_during: str | None = None
    feeling_after: str | None = None

    # Breakeven outcome — only valid when outcome/status is breakeven
    be_outcome: str | None = None

    # QT params — nullable for all non qt-mnq strategies
    qt_fvg_quarter: str | None = None
    qt_entry_quarter: str | None = None
    qt_fvg_date: str | None = None
    qt_fvg_type: str | None = None
    qt_entry_type: str | None = None

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
        """Ensure instrument_type is a valid futures or forex type."""
        if v not in ("forex", "futures_mnq", "futures_mes"):
            raise ValueError("instrument_type must be forex, futures_mnq, or futures_mes")
        return v

    @field_validator("ict_setup_type")
    @classmethod
    def validate_ict_setup_type(cls, v: str | None) -> str | None:
        if v is not None and v not in SETUP_TYPES:
            raise ValueError(f"ict_setup_type must be one of {SETUP_TYPES}")
        return v

    @field_validator("ict_setup_detail")
    @classmethod
    def validate_ict_setup_detail(cls, v: str | None) -> str | None:
        all_details = [d for details in SETUP_DETAIL_MAP.values() for d in details]
        if v is not None and v not in all_details:
            raise ValueError(
                f"ict_setup_detail '{v}' is not a recognised value. "
                f"Valid values: {list(SETUP_DETAIL_MAP.values())}",
            )
        return v

    @field_validator("ict_tp_target")
    @classmethod
    def validate_ict_tp_target(cls, v: str | None) -> str | None:
        if v is not None and v not in TP_TARGETS:
            raise ValueError(f"ict_tp_target must be one of {TP_TARGETS}")
        return v

    @field_validator("ict_ifvg_timeframe")
    @classmethod
    def validate_ict_ifvg_timeframe(cls, v: str | None) -> str | None:
        if v is not None and v not in IFVG_TIMEFRAMES:
            raise ValueError(f"ict_ifvg_timeframe must be one of {IFVG_TIMEFRAMES}")
        return v

    @field_validator("ict_htf_bias")
    @classmethod
    def validate_ict_htf_bias(cls, v: str | None) -> str | None:
        if v is not None and v not in HTF_BIAS_VALUES:
            raise ValueError(f"ict_htf_bias must be one of {HTF_BIAS_VALUES}")
        return v

    @field_validator("feeling_before", "feeling_during", "feeling_after")
    @classmethod
    def validate_feeling(cls, v: str | None) -> str | None:
        """Ensure feeling values belong to the known enum."""
        return _validate_feeling(v)

    @field_validator("be_outcome")
    @classmethod
    def validate_be_outcome(cls, v: str | None) -> str | None:
        if v is not None and v not in ("prevented_loss", "missed_tp"):
            raise ValueError("be_outcome must be 'prevented_loss' or 'missed_tp'")
        return v

    @field_validator("qt_fvg_quarter")
    @classmethod
    def validate_qt_fvg_quarter(cls, v: str | None) -> str | None:
        if v is not None and v not in QT_QUARTERS:
            raise ValueError(f"qt_fvg_quarter must be one of {QT_QUARTERS}")
        return v

    @field_validator("qt_entry_quarter")
    @classmethod
    def validate_qt_entry_quarter(cls, v: str | None) -> str | None:
        if v is not None and v not in QT_QUARTERS:
            raise ValueError(f"qt_entry_quarter must be one of {QT_QUARTERS}")
        return v

    @field_validator("qt_fvg_type")
    @classmethod
    def validate_qt_fvg_type(cls, v: str | None) -> str | None:
        if v is not None and v not in QT_FVG_TYPES:
            raise ValueError(f"qt_fvg_type must be one of {QT_FVG_TYPES}")
        return v

    @field_validator("qt_entry_type")
    @classmethod
    def validate_qt_entry_type(cls, v: str | None) -> str | None:
        if v is not None and v not in QT_ENTRY_TYPES:
            raise ValueError(f"qt_entry_type must be one of {QT_ENTRY_TYPES}")
        return v

    @model_validator(mode="after")
    def validate_ict_detail_matches_type(self) -> "TradeCreateRequest":
        _validate_ict_detail_for_type(self.ict_setup_type, self.ict_setup_detail)
        return self


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
    open_time: datetime | None = None
    close_time: datetime | None = None
    tags: list[str] | None = None
    notes: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    confidence: int | None = Field(default=None, ge=1, le=5)
    rule_followed: bool | None = None
    screenshot_url: str | None = None
    metadata: dict[str, Any] | None = None

    # ICT params — optional on update
    ict_setup_type: str | None = None
    ict_setup_detail: str | None = None
    ict_tp_target: str | None = None
    ict_ifvg_timeframe: str | None = None
    ict_ifvg_bars: int | None = Field(default=None, ge=1, le=100)
    ict_smt_present: bool | None = None
    ict_tdo_aligned: bool | None = None
    ict_htf_bias: str | None = None
    fees: float | None = Field(default=None, ge=0)
    criteria_met_at_entry: bool | None = None

    # Emotional state (MNQ only in practice)
    feeling_before: str | None = None
    feeling_during: str | None = None
    feeling_after: str | None = None

    # Breakeven outcome — only valid when outcome/status is breakeven
    be_outcome: str | None = None

    # QT params — nullable for all non qt-mnq strategies
    qt_fvg_quarter: str | None = None
    qt_entry_quarter: str | None = None
    qt_fvg_date: str | None = None
    qt_fvg_type: str | None = None
    qt_entry_type: str | None = None

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
        """Ensure instrument_type is a valid futures or forex type when provided."""
        if v is not None and v not in ("forex", "futures_mnq", "futures_mes"):
            raise ValueError("instrument_type must be forex, futures_mnq, or futures_mes")
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

    @field_validator("ict_setup_type")
    @classmethod
    def validate_ict_setup_type(cls, v: str | None) -> str | None:
        if v is not None and v not in SETUP_TYPES:
            raise ValueError(f"ict_setup_type must be one of {SETUP_TYPES}")
        return v

    @field_validator("ict_setup_detail")
    @classmethod
    def validate_ict_setup_detail(cls, v: str | None) -> str | None:
        all_details = [d for details in SETUP_DETAIL_MAP.values() for d in details]
        if v is not None and v not in all_details:
            raise ValueError(
                f"ict_setup_detail '{v}' is not a recognised value. "
                f"Valid values: {list(SETUP_DETAIL_MAP.values())}",
            )
        return v

    @field_validator("ict_tp_target")
    @classmethod
    def validate_ict_tp_target(cls, v: str | None) -> str | None:
        if v is not None and v not in TP_TARGETS:
            raise ValueError(f"ict_tp_target must be one of {TP_TARGETS}")
        return v

    @field_validator("ict_ifvg_timeframe")
    @classmethod
    def validate_ict_ifvg_timeframe(cls, v: str | None) -> str | None:
        if v is not None and v not in IFVG_TIMEFRAMES:
            raise ValueError(f"ict_ifvg_timeframe must be one of {IFVG_TIMEFRAMES}")
        return v

    @field_validator("ict_htf_bias")
    @classmethod
    def validate_ict_htf_bias(cls, v: str | None) -> str | None:
        if v is not None and v not in HTF_BIAS_VALUES:
            raise ValueError(f"ict_htf_bias must be one of {HTF_BIAS_VALUES}")
        return v

    @field_validator("feeling_before", "feeling_during", "feeling_after")
    @classmethod
    def validate_feeling(cls, v: str | None) -> str | None:
        """Ensure feeling values belong to the known enum."""
        return _validate_feeling(v)

    @field_validator("be_outcome")
    @classmethod
    def validate_be_outcome(cls, v: str | None) -> str | None:
        if v is not None and v not in ("prevented_loss", "missed_tp"):
            raise ValueError("be_outcome must be 'prevented_loss' or 'missed_tp'")
        return v

    @field_validator("qt_fvg_quarter")
    @classmethod
    def validate_qt_fvg_quarter(cls, v: str | None) -> str | None:
        if v is not None and v not in QT_QUARTERS:
            raise ValueError(f"qt_fvg_quarter must be one of {QT_QUARTERS}")
        return v

    @field_validator("qt_entry_quarter")
    @classmethod
    def validate_qt_entry_quarter(cls, v: str | None) -> str | None:
        if v is not None and v not in QT_QUARTERS:
            raise ValueError(f"qt_entry_quarter must be one of {QT_QUARTERS}")
        return v

    @field_validator("qt_fvg_type")
    @classmethod
    def validate_qt_fvg_type(cls, v: str | None) -> str | None:
        if v is not None and v not in QT_FVG_TYPES:
            raise ValueError(f"qt_fvg_type must be one of {QT_FVG_TYPES}")
        return v

    @field_validator("qt_entry_type")
    @classmethod
    def validate_qt_entry_type(cls, v: str | None) -> str | None:
        if v is not None and v not in QT_ENTRY_TYPES:
            raise ValueError(f"qt_entry_type must be one of {QT_ENTRY_TYPES}")
        return v

    @model_validator(mode="after")
    def validate_ict_detail_matches_type(self) -> "TradeUpdateRequest":
        _validate_ict_detail_for_type(self.ict_setup_type, self.ict_setup_detail)
        return self


class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    signal_id: str | None
    account_id: str | None = None
    # NOT an ORM column — TradeModel has no account_name field.
    # This field must be populated explicitly via trade_to_response().
    # Never use model_validate(orm_instance) directly on TradeResponse;
    # doing so will silently return None here.
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
    rule_followed: bool | None
    linked_mistakes: list[LinkedMistake] = Field(default_factory=list)
    screenshot_url: str | None
    metadata: dict[str, Any] = Field(validation_alias="trade_metadata")
    ict_setup_type: str | None = None
    ict_setup_detail: str | None = None
    ict_tp_target: str | None = None
    ict_ifvg_timeframe: str | None = None
    ict_ifvg_bars: int | None = None
    ict_smt_present: bool | None = None
    ict_tdo_aligned: bool | None = None
    ict_htf_bias: str | None = None
    fees: float | None = None
    criteria_met_at_entry: bool | None = None
    feeling_before: str | None = None
    feeling_during: str | None = None
    feeling_after: str | None = None
    be_outcome: str | None = None
    qt_fvg_quarter: str | None = None
    qt_entry_quarter: str | None = None
    qt_fvg_date: str | None = None
    qt_fvg_type: str | None = None
    qt_entry_type: str | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("open_time", "close_time", "created_at", "updated_at", mode="before")
    @classmethod
    def assume_utc(cls, v: object) -> object:
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


from api.schemas_stats import TradeStatsResponse as TradeStatsResponse  # noqa: F401 — re-export
