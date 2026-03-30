"""
shared/constants.py
-------------------
Project-wide constants shared across all modules (strategies, notifier, API).

Do not put logic here -- only named scalar constants.
"""
from __future__ import annotations

# Slippage assumption used in trade parameter calculations and risk display.
# Measured from real broker data; update here to propagate everywhere.
SLIPPAGE_PIPS: float = 0.2
