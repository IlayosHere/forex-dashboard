"""
config.py
-------------------
Shared spread cost tables and slippage constant for all strategies.

Usage:
    from config import get_spread_pips, SLIPPAGE_PIPS, EXCHANGE_TZ
"""
from __future__ import annotations

from zoneinfo import ZoneInfo


# ---------------------------------------------------------------------------
# Exchange timezone — tvDatafeed returns naive timestamps in the system's
# local timezone.  Set this to match the machine running the scanner.
# ---------------------------------------------------------------------------
EXCHANGE_TZ = ZoneInfo("Asia/Jerusalem")


# ---------------------------------------------------------------------------
# Spread cost model (3-tier: normal / H1 / H0)
# ---------------------------------------------------------------------------
# Measured from logs/spread_monitor.csv (broker-time medians).
# H0 = daily rollover (broker midnight), H1 = transition, H2+ = normal.

# Normal hours (H2-H23)
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

# H1 spreads -- still elevated after rollover (measured medians).
SPREADS_H1: dict[str, float] = {
    "EURUSD": 0.4, "USDJPY": 1.0, "GBPUSD": 0.8, "USDCHF": 0.8,
    "USDCAD": 1.0, "AUDUSD": 1.0, "NZDUSD": 0.5,
    "EURJPY": 1.7, "AUDJPY": 3.3, "CADJPY": 1.6, "CHFJPY": 4.8,
    "AUDCAD": 3.2, "EURCHF": 1.3, "GBPJPY": 2.4,
    "EURAUD": 4.2, "EURCAD": 2.2, "EURNZD": 2.3, "GBPAUD": 3.4,
    "GBPCAD": 2.2, "GBPCHF": 3.0, "GBPNZD": 3.5, "NZDCAD": 1.8,
    "NZDCHF": 1.7, "EURGBP": 0.9, "AUDNZD": 3.6, "NZDJPY": 1.5,
    "CADCHF": 2.2, "AUDCHF": 2.3,
}

# H0 spreads -- daily rollover, extreme widening (measured medians).
SPREADS_H0: dict[str, float] = {
    "EURUSD": 3.6, "USDJPY": 6.7, "GBPUSD": 9.3, "USDCHF": 7.2,
    "USDCAD": 3.2, "AUDUSD": 4.8, "NZDUSD": 2.0,
    "EURJPY": 10.8, "AUDJPY": 14.4, "CADJPY": 9.4, "CHFJPY": 17.0,
    "AUDCAD": 12.2, "EURCHF": 4.7, "GBPJPY": 18.6,
    "EURAUD": 15.0, "EURCAD": 10.2, "EURNZD": 8.8, "GBPAUD": 30.0,
    "GBPCAD": 17.7, "GBPCHF": 18.6, "GBPNZD": 9.1, "NZDCAD": 6.8,
    "NZDCHF": 9.1, "EURGBP": 4.0, "AUDNZD": 13.8, "NZDJPY": 8.0,
    "CADCHF": 9.6, "AUDCHF": 11.0,
}

SLIPPAGE_PIPS: float = 0.3


def get_spread_pips(symbol: str, broker_hour: int) -> float:
    """Return spread in pips for a symbol at a given broker hour.

    Parameters
    ----------
    symbol      : Currency pair (e.g. "EURUSD").
    broker_hour : Hour in broker/server time (0-23).
    """
    if broker_hour == 0:
        return SPREADS_H0.get(symbol, 5.0)
    if broker_hour == 1:
        return SPREADS_H1.get(symbol, 2.0)
    return SPREADS_NORMAL.get(symbol, 1.0)
