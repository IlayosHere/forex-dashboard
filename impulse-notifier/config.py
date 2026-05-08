"""
config.py
-------------------
Shared spread cost tables and slippage constant for all strategies.

Usage:
    from config import get_spread_pips, SLIPPAGE_PIPS
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Spread cost model (3-tier: normal / H1 / H0)
# ---------------------------------------------------------------------------
# Measured from logs/spread_monitor.csv (broker-time medians).
# H0 = daily rollover (broker midnight), H1 = transition, H2+ = normal.

SPREADS_NORMAL: dict[str, float] = {
    "EURUSD": 0.2, "USDJPY": 0.3, "GBPUSD": 0.4, "USDCHF": 0.5,
    "USDCAD": 0.5, "AUDUSD": 0.3, "NZDUSD": 0.4,
    "EURJPY": 1.2, "AUDJPY": 1.2, "CADJPY": 1.1, "CHFJPY": 2.0,
    "AUDCAD": 0.9, "EURCHF": 0.6, "GBPJPY": 1.2,
    "EURAUD": 1.2, "EURCAD": 1.3, "EURNZD": 1.8, "GBPAUD": 2.0,
    "GBPCAD": 1.8, "GBPCHF": 1.5, "GBPNZD": 2.5, "NZDCAD": 1.8,
    "NZDCHF": 1.5, "EURGBP": 0.9, "AUDNZD": 2.0, "NZDJPY": 1.1,
    "CADCHF": 1.5, "AUDCHF": 1.4,
}

SLIPPAGE_PIPS: float = 0.3


def get_spread_pips(symbol: str) -> float:
    """Return spread in pips for a symbol."""
    return SPREADS_NORMAL.get(symbol, 1.0)
