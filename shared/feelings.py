"""
shared/feelings.py
------------------
Single source of truth for the trading feelings enum.

Used by:
  - api/schemas_trade.py   (field validation)
  - api/schemas_session.py (field validation)
  - api/models.py          (reference for column values)
"""
from __future__ import annotations

FEELING_VALUES: list[str] = [
    "calm",
    "focused",
    "confident",
    "anxious",
    "impatient",
    "fearful",
    "greedy",
    "distracted",
    "revenge",
    "tired",
]

POSITIVE_FEELINGS: frozenset[str] = frozenset({"calm", "focused", "confident"})
NEGATIVE_FEELINGS: frozenset[str] = frozenset(
    {"anxious", "impatient", "fearful", "greedy", "distracted", "revenge", "tired"}
)
