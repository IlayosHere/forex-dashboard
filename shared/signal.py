"""
shared/signal.py
----------------
Signal dataclass — the contract between strategy scanners and the API.

Every scanner must return list[Signal]. Fields are frozen; add strategy-specific
data to metadata: dict instead of adding new required fields here.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


def generate_id() -> str:
    """Return a new UUID4 string suitable for use as a Signal primary key."""
    return str(uuid.uuid4())


@dataclass
class Signal:
    strategy: str       # matches the folder name and URL slug, e.g. "fvg-impulse"
    symbol: str         # e.g. "EURUSD"
    direction: str      # "BUY" or "SELL"
    candle_time: datetime  # UTC, when the signal candle closed
    entry: float        # close price of signal candle
    sl: float           # suggested stop loss (user can override in UI)
    tp: float           # suggested take profit (user can override in UI)
    lot_size: float     # pre-calculated at default account settings
    risk_pips: float
    spread_pips: float
    metadata: dict      # strategy-specific extras — free-form, rendered as key-value

    id: str = field(default_factory=generate_id)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
