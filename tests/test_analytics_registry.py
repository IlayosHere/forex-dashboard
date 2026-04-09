"""
tests/test_analytics_registry.py
---------------------------------
Unit tests for analytics/registry.py: @register, get_params_for_strategy,
resolve_all_params, get_param_def.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pandas as pd

from analytics.registry import (
    _PARAMS,
    get_param_def,
    get_params_for_strategy,
    register,
    resolve_all_params,
)
from analytics.types import ParamDef


# ---------------------------------------------------------------------------
# @register decorator
# ---------------------------------------------------------------------------


def test_register_adds_param_to_registry() -> None:
    name = "_test_reg_add"
    try:

        @register(name, dtype="float")
        def dummy(signal: Any, candles: pd.DataFrame | None) -> float:
            return 1.0

        assert name in _PARAMS
        pdef = _PARAMS[name]
        assert pdef.name == name
        assert pdef.dtype == "float"
        assert pdef.needs_candles is False
        assert "*" in pdef.strategies
    finally:
        _PARAMS.pop(name, None)


def test_register_with_strategy_and_candles() -> None:
    name = "_test_reg_strat"
    try:

        @register(
            name,
            strategies=frozenset({"test-strat"}),
            needs_candles=True,
            dtype="str",
        )
        def dummy(signal: Any, candles: pd.DataFrame | None) -> str:
            return "x"

        pdef = _PARAMS[name]
        assert pdef.strategies == frozenset({"test-strat"})
        assert pdef.needs_candles is True
        assert pdef.dtype == "str"
    finally:
        _PARAMS.pop(name, None)


# ---------------------------------------------------------------------------
# get_params_for_strategy
# ---------------------------------------------------------------------------


def test_get_params_includes_wildcard() -> None:
    """Shared params (strategy='*') should appear for any strategy."""
    params = get_params_for_strategy("fvg-impulse")
    names = {p.name for p in params}
    assert "session_label" in names
    assert "day_of_week" in names
    assert "spread_risk_ratio" in names


def test_get_params_includes_strategy_specific() -> None:
    params = get_params_for_strategy("fvg-impulse")
    names = {p.name for p in params}
    assert "fvg_age" in names
    assert "fvg_width_pips" in names


def test_get_params_excludes_other_strategy() -> None:
    params = get_params_for_strategy("fvg-impulse")
    names = {p.name for p in params}
    assert "bos_used" not in names  # nova-candle only


def test_get_params_nova_candle() -> None:
    params = get_params_for_strategy("nova-candle")
    names = {p.name for p in params}
    assert "bos_used" in names
    assert "body_pips" in names
    assert "fvg_age" not in names  # fvg-impulse only


# ---------------------------------------------------------------------------
# get_param_def
# ---------------------------------------------------------------------------


def test_get_param_def_found() -> None:
    pdef = get_param_def("session_label")
    assert pdef is not None
    assert pdef.name == "session_label"


def test_get_param_def_not_found() -> None:
    assert get_param_def("nonexistent_param_xyz") is None


# ---------------------------------------------------------------------------
# resolve_all_params
# ---------------------------------------------------------------------------


def test_resolve_all_params_no_candles_skips_candle_params() -> None:
    signal = MagicMock()
    signal.candle_time.hour = 10
    signal.candle_time.weekday.return_value = 2
    signal.spread_pips = 1.0
    signal.risk_pips = 10.0
    signal.symbol = "EURUSD"

    result = resolve_all_params(signal, "fvg-impulse", candles=None)
    assert "session_label" in result
    assert "day_of_week" in result
    # Candle-dependent params should be absent (skipped, not None)
    assert "atr_14" not in result
    assert "trend_h1_aligned" not in result


def test_resolve_all_params_catches_errors() -> None:
    """A failing param should return None, not crash the batch."""
    name = "_test_error_param"
    try:

        @register(name, dtype="float")
        def bad_param(signal: Any, candles: pd.DataFrame | None) -> float:
            msg = "boom"
            raise ValueError(msg)

        signal = MagicMock()
        signal.candle_time.hour = 10
        signal.candle_time.weekday.return_value = 2
        signal.spread_pips = 1.0
        signal.risk_pips = 10.0
        signal.symbol = "EURUSD"

        result = resolve_all_params(signal, "fvg-impulse", candles=None)
        assert result[name] is None
        assert "session_label" in result  # other params still computed
    finally:
        _PARAMS.pop(name, None)
