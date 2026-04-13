"""
analytics/registry.py
---------------------
Parameter registry — ``@register`` decorator and resolution helpers.

Follows the same decorator-registry pattern as ``shared/notifier/_registry.py``.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from analytics.types import ParamDef

logger = logging.getLogger(__name__)

_PARAMS: dict[str, ParamDef] = {}


def register(
    name: str,
    *,
    strategies: frozenset[str] = frozenset({"*"}),
    needs_candles: bool = False,
    dtype: str = "float",
) -> Callable[[Any], Any]:
    """Decorator that registers a parameter computation function.

    Parameters
    ----------
    name : str
        Unique parameter name (also the dict key in resolved output).
    strategies : frozenset[str]
        Set of strategy slugs this param applies to, or ``{"*"}`` for all.
    needs_candles : bool
        Whether the function requires a candle DataFrame (second arg).
    dtype : str
        Return type hint — one of "float", "str", "int", "bool".
    """
    def decorator(fn: Any) -> Any:
        _PARAMS[name] = ParamDef(
            name=name,
            fn=fn,
            strategies=strategies,
            needs_candles=needs_candles,
            dtype=dtype,
        )
        return fn
    return decorator


def get_param_def(name: str) -> ParamDef | None:
    """Return a single ParamDef by name, or None if not registered."""
    return _PARAMS.get(name)


def get_params_for_strategy(strategy: str) -> list[ParamDef]:
    """Return params where strategy is ``'*'`` or matches exactly."""
    return [
        p for p in _PARAMS.values()
        if "*" in p.strategies or strategy in p.strategies
    ]


def resolve_all_params(
    signal: Any,
    strategy: str,
    candles: Any = None,
) -> dict[str, Any]:
    """Run all applicable params for a signal.

    Skips params that need candles when *candles* is ``None``.
    Catches errors per-param and logs them — never crashes the caller.
    """
    results: dict[str, Any] = {}
    for param in get_params_for_strategy(strategy):
        if param.needs_candles and candles is None:
            continue
        try:
            results[param.name] = param.fn(signal, candles)
        except Exception:
            logger.exception("Error computing param %r for signal", param.name)
            results[param.name] = None
    return results
