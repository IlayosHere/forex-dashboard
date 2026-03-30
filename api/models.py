"""
api/models.py
-------------
SQLAlchemy 2.0 ORM models for the Forex Signal Dashboard.

Models:
  - SignalModel: strategy signals
  - TradeModel: trade journal entries
  - AccountModel: trading accounts (demo, live, funded)

Fields mirror shared.signal.Signal exactly. The `metadata` dict is stored as
a JSON column named `signal_metadata` — "metadata" is a reserved attribute name
on SQLAlchemy's DeclarativeBase and cannot be used as a mapped column name.

Indexes on strategy and candle_time support the two most common query patterns:
  - Filter by strategy (GET /api/signals?strategy=fvg-impulse)
  - Sort by recency (ORDER BY candle_time DESC)
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from api.db import Base


class SignalModel(Base):
    __tablename__ = "signals"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)
    candle_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    entry: Mapped[float] = mapped_column(Float, nullable=False)
    sl: Mapped[float] = mapped_column(Float, nullable=False)
    tp: Mapped[float] = mapped_column(Float, nullable=False)
    lot_size: Mapped[float] = mapped_column(Float, nullable=False)
    risk_pips: Mapped[float] = mapped_column(Float, nullable=False)
    spread_pips: Mapped[float] = mapped_column(Float, nullable=False)
    signal_metadata: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_signals_strategy", "strategy"),
        Index("ix_signals_candle_time", "candle_time"),
    )


class AccountModel(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    account_type: Mapped[str] = mapped_column(String, nullable=False)  # demo, live, funded
    instrument_type: Mapped[str] = mapped_column(String, nullable=False)  # forex, futures_mnq
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")  # active, passed, failed, closed
    prop_firm: Mapped[str | None] = mapped_column(String, nullable=True)
    phase: Mapped[str | None] = mapped_column(String, nullable=True)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_accounts_account_type", "account_type"),
        Index("ix_accounts_instrument_type", "instrument_type"),
        Index("ix_accounts_status", "status"),
    )


class TradeModel(Base):
    __tablename__ = "trades"

    # Identity
    id: Mapped[str] = mapped_column(String, primary_key=True)
    signal_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("signals.id"), nullable=True
    )
    account_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("accounts.id"), nullable=True
    )

    # Trade setup
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    instrument_type: Mapped[str] = mapped_column(String, nullable=False, default="forex")
    direction: Mapped[str] = mapped_column(String, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    sl_price: Mapped[float] = mapped_column(Float, nullable=False)
    tp_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    lot_size: Mapped[float] = mapped_column(Float, nullable=False)

    # Status & outcome
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    outcome: Mapped[str | None] = mapped_column(String, nullable=True)

    # P&L (server-calculated on close)
    pnl_pips: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    rr_achieved: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_pips: Mapped[float] = mapped_column(Float, nullable=False)

    # Timing
    open_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    close_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Assessment
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str] = mapped_column(String, nullable=False, default="")
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    screenshot_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # Extensibility
    trade_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_trades_strategy", "strategy"),
        Index("ix_trades_symbol", "symbol"),
        Index("ix_trades_status", "status"),
        Index("ix_trades_open_time", "open_time"),
        Index("ix_trades_outcome", "outcome"),
        Index("ix_trades_instrument_type", "instrument_type"),
        Index("ix_trades_account_id", "account_id"),
    )
