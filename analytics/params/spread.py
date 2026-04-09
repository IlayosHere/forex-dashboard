"""
analytics/params/spread.py
--------------------------
Spread and pair classification parameters.
"""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from analytics.registry import register
from analytics.types import PairCategory

logger = logging.getLogger(__name__)

_MAJORS: frozenset[str] = frozenset({
    "EURUSD", "USDJPY", "GBPUSD", "USDCHF",
    "USDCAD", "AUDUSD", "NZDUSD",
})


@register("spread_risk_ratio", dtype="float")
def spread_risk_ratio(
    signal: Any,
    _candles: pd.DataFrame | None,
) -> float | None:
    """Return spread_pips / risk_pips, or None on zero division."""
    if signal.risk_pips == 0:
        return None
    return signal.spread_pips / signal.risk_pips


@register("pair_category", dtype="str")
def pair_category(signal: Any, _candles: pd.DataFrame | None) -> str:
    """Classify the symbol as MAJOR, JPY_CROSS, or MINOR_CROSS."""
    symbol: str = signal.symbol
    if symbol in _MAJORS:
        return PairCategory.MAJOR.value
    if symbol.endswith("JPY"):
        return PairCategory.JPY_CROSS.value
    return PairCategory.MINOR_CROSS.value
