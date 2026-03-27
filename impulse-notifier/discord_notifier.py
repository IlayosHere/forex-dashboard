"""
Discord webhook sender for FVG wick-test alerts.

Formats signals as Discord embeds and POSTs to a webhook URL.
Best-effort delivery -- errors are logged, never raised.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests

from calculations import _fmt_price

logger = logging.getLogger(__name__)

COLOR_BUY = 0x00FF00   # Green
COLOR_SELL = 0xFF4444   # Red


def _build_embed(signal: Dict[str, Any]) -> dict:
    """Build a Discord embed dict from a signal."""
    direction = signal["direction"]
    symbol = signal["symbol"]
    color = COLOR_BUY if direction == "BUY" else COLOR_SELL

    candle_time = signal["candle_time"]
    time_str = candle_time.strftime("%Y-%m-%d %H:%M UTC")

    fmt = lambda p: _fmt_price(symbol, p)

    fields = [
        {"name": "Symbol",        "value": symbol,                                    "inline": True},
        {"name": "Direction",     "value": direction,                                 "inline": True},
        {"name": "Signal Time",   "value": time_str,                                  "inline": True},
        {"name": "Entry (close)", "value": fmt(signal["entry_price"]),                "inline": True},
        {"name": "SL",            "value": fmt(signal["sl"]),                         "inline": True},
        {"name": "TP",            "value": fmt(signal["tp"]),                         "inline": True},
        {"name": "Lot Size",      "value": f"{signal['lot_size']:.2f}",               "inline": True},
        {"name": "Risk (pips)",   "value": f"{signal['risk_pips']} pips (incl. {signal['spread_pips']}p spread + 0.2p slip)", "inline": False},
        {"name": "FVG Width",     "value": f"{signal['fvg_width_pips']} pips",        "inline": True},
        {"name": "Near Edge",     "value": fmt(signal["fvg_near_edge"]),              "inline": True},
        {"name": "FVG Age",       "value": f"{signal['fvg_age']} bars",               "inline": True},
    ]

    return {
        "title": f"[FVG] {direction} Signal: {symbol}",
        "description": f"Virgin FVG wick-test rejection on M15",
        "color": color,
        "fields": fields,
        "footer": {"text": "FVG Identifier"},
    }


def send_discord_alert(webhook_url: str, signals: List[Dict[str, Any]]) -> None:
    """Send FVG signals to Discord via webhook.

    Parameters
    ----------
    webhook_url : str
        Discord webhook URL. If empty, alerts are skipped.
    signals : list
        List of signal dicts from the scanner.
    """
    if not webhook_url:
        logger.warning("No webhook URL configured, skipping Discord alert")
        return

    for signal in signals:
        try:
            embed = _build_embed(signal)
            payload = {"embeds": [embed]}
            resp = requests.post(webhook_url, json=payload, timeout=5)
            if resp.status_code in (200, 204):
                logger.debug("Discord alert sent for %s %s",
                             signal["symbol"], signal["direction"])
            else:
                logger.warning("Discord webhook returned %d: %s",
                               resp.status_code, resp.text[:200])
        except Exception:
            logger.exception("Failed to send Discord alert for %s", signal["symbol"])
