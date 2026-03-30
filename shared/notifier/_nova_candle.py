"""
shared/notifier/_nova_candle.py
--------------------------------
Discord embed builder for nova-candle signals.

Registered automatically when this module is imported by _registry.py.
"""
from __future__ import annotations

from shared.notifier._base import embed_base, fmt_price, fmt_time
from shared.notifier._registry import register
from shared.signal import Signal


@register("nova-candle")
def build_nova_candle_embed(sig: Signal) -> dict:
    """Build a Discord embed for a nova-candle Signal.

    Strategy-specific fields appended after common fields:
    BOS Candle Time and BOS Swing Price.
    Both may be None (fallback path when no BOS swing is found);
    None values render as "N/A" rather than crashing.

    Parameters
    ----------
    sig : Signal
        Signal with strategy == "nova-candle".

    Returns
    -------
    dict
        Discord embed dict.
    """
    embed = embed_base(
        sig,
        title=f"[Nova] {sig.direction} Signal: {sig.symbol}",
        description="Wickless momentum candle on M15",
    )
    m = sig.metadata
    bos_price = m.get("bos_swing_price")
    bos_price_str = fmt_price(sig.symbol, bos_price) if bos_price is not None else "N/A"

    embed["fields"].extend([
        {
            "name": "BOS Candle",
            "value": fmt_time(m.get("bos_candle_time")),
            "inline": True,
        },
        {
            "name": "BOS Swing Price",
            "value": bos_price_str,
            "inline": True,
        },
    ])
    return embed
