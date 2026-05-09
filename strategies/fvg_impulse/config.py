"""
config.py
-------------------
Shared spread cost tables and slippage constant for all strategies.

H0/H1 tiers removed: signals during broker hours 0-1 are suppressed at the
scanner level, so only normal-hours spreads are needed.

Usage:
    from config import get_spread_pips, SLIPPAGE_PIPS, EXCHANGE_TZ
"""
from __future__ import annotations

from shared.market_data import EXCHANGE_TZ  # noqa: F401 — re-exported for strategy-local imports


# ---------------------------------------------------------------------------
# Spread cost model (single tier: normal hours H2+)
# ---------------------------------------------------------------------------
# Measured from logs/spread_monitor.csv (broker-time medians).
# H0/H1 signals are suppressed in the scanner; these values cover H2-H23.

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

SLIPPAGE_PIPS: float = 0.2


def get_spread_pips(symbol: str) -> float:
    """Return normal-hours spread in pips for a symbol.

    Parameters
    ----------
    symbol : Currency pair (e.g. "EURUSD").
    """
    return SPREADS_NORMAL.get(symbol, 1.0)
