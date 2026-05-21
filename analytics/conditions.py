"""
analytics/conditions.py
-----------------------
Pure condition evaluator. No DB, no I/O, no side effects.

Used by gates (live signal filtering) and experiments (historical backtesting).
The same condition grammar is serialized over the API and persisted in the DB.
"""
from __future__ import annotations

from typing import Any, Literal

Operator = Literal["eq", "ne", "in", "not_in", "gte", "lte", "between", "is_null", "not_null"]

OPERATORS: frozenset[str] = frozenset(
    {"eq", "ne", "in", "not_in", "gte", "lte", "between", "is_null", "not_null"}
)


class ConditionError(ValueError):
    """Raised when a condition dict is structurally invalid."""


def validate(condition: dict[str, Any]) -> None:
    """Raise ConditionError if the condition dict is malformed."""
    op = condition.get("op")
    if op not in OPERATORS:
        raise ConditionError(f"Unknown operator: {op!r}")
    if not condition.get("param"):
        raise ConditionError("Missing 'param' field")
    if op in ("in", "not_in") and not isinstance(condition.get("values"), list):
        raise ConditionError(f"Operator '{op}' requires a 'values' list")
    if op == "between":
        if condition.get("low") is None or condition.get("high") is None:
            raise ConditionError("Operator 'between' requires 'low' and 'high'")
    if op in ("eq", "ne", "gte", "lte") and "value" not in condition:
        raise ConditionError(f"Operator '{op}' requires a 'value' field")


def evaluate(condition: dict[str, Any], params: dict[str, Any]) -> bool:
    """Return True iff the condition is satisfied by the given param dict.

    Null values fail all comparison operators except is_null/not_null.
    """
    name: str = condition["param"]
    op: str = condition["op"]
    val = params.get(name)

    if op == "is_null":
        return val is None
    if op == "not_null":
        return val is not None
    if val is None:
        return False
    if op == "eq":
        return _coerce(val) == _coerce(condition["value"])
    if op == "ne":
        return _coerce(val) != _coerce(condition["value"])
    if op == "in":
        return _coerce(val) in [_coerce(v) for v in condition["values"]]
    if op == "not_in":
        return _coerce(val) not in [_coerce(v) for v in condition["values"]]
    if op == "gte":
        return float(val) >= float(condition["value"])
    if op == "lte":
        return float(val) <= float(condition["value"])
    if op == "between":
        return float(condition["low"]) <= float(val) <= float(condition["high"])
    raise ConditionError(f"Unknown operator: {op!r}")


def evaluate_all(
    conditions: list[dict[str, Any]],
    params: dict[str, Any],
) -> tuple[bool, list[int]]:
    """Evaluate every condition with AND combining.

    Returns (overall_pass, list_of_failed_indices).
    An empty condition list passes with no failures.
    """
    failed = [i for i, c in enumerate(conditions) if not evaluate(c, params)]
    return (len(failed) == 0, failed)


def _coerce(value: Any) -> Any:
    """Normalise booleans to strings so True == 'True' comparisons work."""
    if isinstance(value, bool):
        return str(value)
    return value
