"""
api/models.py
-------------
SQLAlchemy 2.0 ORM models for the Trade Journal.

Models:
  - UserModel: authenticated users
  - AccountModel: trading accounts (demo, live, funded)
  - TradeModel: trade journal entries
  - LifeEntryModel: personal life journal entries
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.db import Base


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_users_username", "username", unique=True),
    )


class AccountModel(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    account_type: Mapped[str] = mapped_column(String, nullable=False)  # demo, live, funded
    instrument_type: Mapped[str] = mapped_column(String, nullable=False)  # futures (account-level); futures_mnq, futures_mes (trade-level)
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")  # active, passed, failed, closed
    prop_firm: Mapped[str | None] = mapped_column(String, nullable=True)
    phase: Mapped[str | None] = mapped_column(String, nullable=True)
    balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    owner: Mapped[str] = mapped_column(String, nullable=False, default="admin")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_accounts_account_type", "account_type"),
        Index("ix_accounts_instrument_type", "instrument_type"),
        Index("ix_accounts_status", "status"),
        Index("ix_accounts_owner", "owner"),
    )


class TradeModel(Base):
    __tablename__ = "trades"

    # Identity
    id: Mapped[str] = mapped_column(String, primary_key=True)
    signal_id: Mapped[str | None] = mapped_column(String, nullable=True)
    # No FK constraint — same reasoning as signal_id (see migrate_drop_signals_fk):
    # a trade should keep its scenario reference even if the scenario itself is later pruned.
    scenario_id: Mapped[str | None] = mapped_column(String, nullable=True)
    account_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=True
    )

    account: Mapped[AccountModel | None] = relationship(lazy="noload")

    # Trade setup
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    instrument_type: Mapped[str] = mapped_column(String, nullable=False, default="futures")
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
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    notes: Mapped[str] = mapped_column(String, nullable=False, default="")
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule_followed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    screenshot_url: Mapped[str | None] = mapped_column(String, nullable=True)

    # ICT trade params (MNQ only — nullable for all other strategies)
    ict_setup_type: Mapped[str | None] = mapped_column(String, nullable=True)
    ict_setup_detail: Mapped[str | None] = mapped_column(String, nullable=True)
    ict_tp_target: Mapped[str | None] = mapped_column(String, nullable=True)
    ict_ifvg_timeframe: Mapped[str | None] = mapped_column(String, nullable=True)
    ict_smt_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ict_tdo_aligned: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ict_cisd_present: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    ict_htf_bias: Mapped[str | None] = mapped_column(String, nullable=True)    # aligned / counter / neutral
    ict_ifvg_bars: Mapped[int | None] = mapped_column(Integer, nullable=True)   # bars from FVG to IFVG trigger
    fees: Mapped[float | None] = mapped_column(Float, nullable=True)             # broker fees/commission (USD)
    criteria_met_at_entry: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # QT trade params (qt-mnq only — nullable for all other strategies)
    qt_fvg_quarter: Mapped[str | None] = mapped_column(String, nullable=True)
    qt_entry_quarter: Mapped[str | None] = mapped_column(String, nullable=True)
    qt_fvg_date: Mapped[str | None] = mapped_column(String, nullable=True)
    qt_fvg_type: Mapped[str | None] = mapped_column(String, nullable=True)
    qt_entry_type: Mapped[str | None] = mapped_column(String, nullable=True)

    # Emotional state (MNQ only in practice — nullable for all)
    feeling_before: Mapped[str | None] = mapped_column(String, nullable=True)
    feeling_during: Mapped[str | None] = mapped_column(String, nullable=True)
    feeling_after: Mapped[str | None] = mapped_column(String, nullable=True)

    # Breakeven outcome — only meaningful when outcome = 'breakeven'
    # 'prevented_loss': BE stop saved from a losing trade
    # 'missed_tp': BE stop cut off a trade that would have hit TP
    be_outcome: Mapped[str | None] = mapped_column(String, nullable=True)

    # Trade location — live trades only (None for backtest); 'home' | 'phone' | 'pc_outside'
    trade_location: Mapped[str | None] = mapped_column(String, nullable=True)

    # Extensibility
    trade_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Ownership
    owner: Mapped[str] = mapped_column(String, nullable=False, default="admin")

    __table_args__ = (
        Index("ix_trades_strategy", "strategy"),
        Index("ix_trades_symbol", "symbol"),
        Index("ix_trades_status", "status"),
        Index("ix_trades_open_time", "open_time"),
        Index("ix_trades_outcome", "outcome"),
        Index("ix_trades_instrument_type", "instrument_type"),
        Index("ix_trades_account_id", "account_id"),
        Index("ix_trades_owner", "owner"),
        Index("ix_trades_owner_open_time", "owner", "open_time"),
        Index("ix_trades_owner_status", "owner", "status"),
    )


class TradingSessionModel(Base):
    """One session journal entry per trader per calendar date."""

    __tablename__ = "trading_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner: Mapped[str] = mapped_column(String, nullable=False, default="admin")
    date: Mapped[date] = mapped_column(Date, nullable=False)
    had_pre_session_plan: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    feeling_pre: Mapped[str | None] = mapped_column(String, nullable=True)
    feeling_during: Mapped[str | None] = mapped_column(String, nullable=True)
    feeling_post: Mapped[str | None] = mapped_column(String, nullable=True)
    session_notes: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_trading_sessions_owner", "owner"),
        Index("ix_trading_sessions_owner_date", "owner", "date"),
        UniqueConstraint("owner", "date", name="uq_session_owner_date"),
    )


class MistakeModel(Base):
    __tablename__ = "mistakes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner: Mapped[str] = mapped_column(String, nullable=False, default="admin")
    name: Mapped[str] = mapped_column(String, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_mistakes_owner", "owner"),
        UniqueConstraint("owner", "name", name="uq_mistake_owner_name"),
    )


class TradeMistakeModel(Base):
    """Join table linking trades to mistakes (many-to-many)."""

    __tablename__ = "trade_mistakes"

    trade_id: Mapped[str] = mapped_column(
        String, ForeignKey("trades.id", ondelete="CASCADE"), primary_key=True,
    )
    mistake_id: Mapped[str] = mapped_column(
        String, ForeignKey("mistakes.id", ondelete="CASCADE"), primary_key=True,
    )
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class RuleCategoryModel(Base):
    """A user-defined category label that groups trading rules."""

    __tablename__ = "rule_categories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    owner: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    rules: Mapped[list[RuleModel]] = relationship(
        "RuleModel", back_populates="category_rel", lazy="noload",
    )

    __table_args__ = (
        Index("ix_rule_categories_owner", "owner"),
        UniqueConstraint("owner", "name", name="uq_rule_category_owner_name"),
    )


class RuleModel(Base):
    """A trading rule written by the trader."""

    __tablename__ = "rules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    owner: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String(80), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("rule_categories.id", ondelete="SET NULL"), nullable=True,
    )
    break_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    category_rel: Mapped[RuleCategoryModel | None] = relationship(
        "RuleCategoryModel", back_populates="rules", lazy="noload",
    )
    mistake_links: Mapped[list[RuleMistakeLink]] = relationship(
        "RuleMistakeLink", back_populates="rule", lazy="noload",
    )

    __table_args__ = (
        Index("ix_rules_owner", "owner"),
        Index("ix_rules_category_id", "category_id"),
    )


class RuleMistakeLink(Base):
    """Association table linking rules to mistakes (many-to-many)."""

    __tablename__ = "rule_mistake_links"

    rule_id: Mapped[str] = mapped_column(
        String, ForeignKey("rules.id", ondelete="CASCADE"), primary_key=True,
    )
    mistake_id: Mapped[str] = mapped_column(
        String, ForeignKey("mistakes.id", ondelete="CASCADE"), primary_key=True,
    )
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    rule: Mapped[RuleModel] = relationship(
        "RuleModel", back_populates="mistake_links", lazy="noload",
    )


class LifeEntryModel(Base):
    """Personal life journal entry — free-form text with optional mood and tags."""

    __tablename__ = "life_entries"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    owner: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    mood: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_life_entries_owner", "owner"),
        Index("ix_life_entries_owner_entry_at", "owner", "entry_at"),
    )
