"""
analytics/types.py
------------------
Core types shared across the analytics engine.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

import pandas as pd


class Session(Enum):
    """Trading session based on UTC hour."""

    ASIAN = "ASIAN"
    LONDON = "LONDON"
    NY_OVERLAP = "NY_OVERLAP"
    NY_LATE = "NY_LATE"
    CLOSE = "CLOSE"


class PairCategory(Enum):
    """Broad currency-pair classification."""

    MAJOR = "MAJOR"
    JPY_CROSS = "JPY_CROSS"
    MINOR_CROSS = "MINOR_CROSS"


WIN_RESOLUTION = "TP_HIT"
LOSS_RESOLUTION = "SL_HIT"

ParamFn = Callable[[Any, pd.DataFrame | None], float | str | int | bool | None]


@dataclass(frozen=True)
class ParamDef:
    """Metadata + callable for a single computed parameter."""

    name: str
    fn: ParamFn
    strategies: frozenset[str]
    needs_candles: bool
    dtype: Literal["float", "str", "int", "bool"]
