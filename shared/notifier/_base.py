"""
shared/notifier/_base.py
------------------------
Shared embed primitives: colors, EmbedBuilder Protocol, common field builder,
price/time formatters, and the embed_base factory used by every strategy builder.
"""
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from shared.constants import SLIPPAGE_PIPS
from shared.signal import Signal

# Discord embed colors
COLOR_BUY: int = 0x00FF00
COLOR_SELL: int = 0xFF4444

TIMEFRAME_LABEL: str = "M15"


class EmbedBuilder(Protocol):
    """Protocol for strategy-specific embed builder functions."""

    def __call__(self, sig: Signal) -> dict: ...


def fmt_price(symbol: str, price: float) -> str:
    """Format a price with symbol-appropriate decimal places.

    Parameters
    ----------
    symbol : str
        Currency pair, e.g. "USDJPY" or "EURUSD".
    price : float
        Price to format.

    Returns
    -------
    str
        3 decimal places for JPY pairs, 5 for all others.
    """
    decimals = 3 if "JPY" in symbol.upper() else 5
    return f"{price:.{decimals}f}"


def fmt_time(value: str | datetime | None) -> str:
    """Format an ISO string or datetime as a readable UTC timestamp.

    Parameters
    ----------
    value : str, datetime, or None
        Value to format. None returns "N/A".

    Returns
    -------
    str
        Human-readable UTC timestamp, or "N/A" if value is None.
    """
    if value is None:
        return "N/A"
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return value
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    return value.strftime("%Y-%m-%d %H:%M UTC")


def build_common_fields(sig: Signal) -> list[dict]:
    """Return the Discord embed fields shared by all strategies.

    Parameters
    ----------
    sig : Signal
        Signal to extract common fields from.

    Returns
    -------
    list[dict]
        Nine Discord embed field dicts: Symbol, Direction, Signal Time,
        Entry, SL, TP, Lot Size, Risk (pips), Spread.
    """
    time_str = sig.candle_time.strftime("%Y-%m-%d %H:%M UTC")
    fmt = lambda p: fmt_price(sig.symbol, p)
    risk_detail = (
        f"{sig.risk_pips:.1f} pips "
        f"(incl. {sig.spread_pips:.1f}p spread + {SLIPPAGE_PIPS}p slip)"
    )
    return [
        {"name": "Symbol",      "value": sig.symbol,             "inline": True},
        {"name": "Direction",   "value": sig.direction,          "inline": True},
        {"name": "Signal Time", "value": time_str,               "inline": True},
        {"name": "Entry",       "value": fmt(sig.entry),         "inline": True},
        {"name": "SL",          "value": fmt(sig.sl),            "inline": True},
        {"name": "TP",          "value": fmt(sig.tp),            "inline": True},
        {"name": "Lot Size",    "value": f"{sig.lot_size:.2f}",  "inline": True},
        {"name": "Risk (pips)", "value": risk_detail,            "inline": False},
        {"name": "Spread",      "value": f"{sig.spread_pips:.1f}p", "inline": True},
    ]


def embed_base(sig: Signal, title: str, description: str) -> dict:
    """Build a Discord embed dict pre-populated with common fields.

    Parameters
    ----------
    sig : Signal
        The signal to embed.
    title : str
        Embed title shown in Discord.
    description : str
        Short description line below the title.

    Returns
    -------
    dict
        Discord embed dict. Callers may append strategy-specific field
        dicts to embed["fields"] before returning.
    """
    color = COLOR_BUY if sig.direction == "BUY" else COLOR_SELL
    return {
        "title": title,
        "description": description,
        "color": color,
        "fields": build_common_fields(sig),
        "footer": {"text": f"{sig.strategy} · {TIMEFRAME_LABEL}"},
    }
