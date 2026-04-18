"""
shared/notifier/_fvg_impulse_5m.py
------------------------------------
Discord embed builder for fvg-impulse-5m signals.

Registered automatically when this module is imported by _registry.py.
"""
from __future__ import annotations

from shared.notifier._base import embed_base, fmt_price, fmt_time
from shared.notifier._registry import register
from shared.signal import Signal

TIMEFRAME_LABEL: str = "M5"


@register("fvg-impulse-5m")
def build_fvg_impulse_5m_embed(sig: Signal) -> dict:
    """Build a Discord embed for an fvg-impulse-5m Signal.

    Strategy-specific fields appended after common fields:
    FVG Width, Near Edge, Far Edge, FVG Age, Formation Time.
    All metadata keys use .get() with safe defaults so a partially-populated
    metadata dict never raises KeyError.

    Parameters
    ----------
    sig : Signal
        Signal with strategy == "fvg-impulse-5m".

    Returns
    -------
    dict
        Discord embed dict.
    """
    embed = embed_base(
        sig,
        title=f"[FVG 5m] {sig.direction} Signal: {sig.symbol}",
        description="Virgin FVG wick-test rejection on M5",
    )
    embed["footer"] = {"text": f"{sig.strategy} · {TIMEFRAME_LABEL}"}
    fmt = lambda p: fmt_price(sig.symbol, p)
    m = sig.metadata

    near = m.get("fvg_near_edge")
    far = m.get("fvg_far_edge")

    embed["fields"].extend([
        {
            "name": "FVG Width",
            "value": f"{m.get('fvg_width_pips', 'N/A')} pips",
            "inline": True,
        },
        {
            "name": "Near Edge",
            "value": fmt(near) if near is not None else "N/A",
            "inline": True,
        },
        {
            "name": "Far Edge",
            "value": fmt(far) if far is not None else "N/A",
            "inline": True,
        },
        {
            "name": "FVG Age",
            "value": f"{m.get('fvg_age', 'N/A')} bars",
            "inline": True,
        },
        {
            "name": "Formation Time",
            "value": fmt_time(m.get("fvg_formation_time")),
            "inline": True,
        },
    ])
    return embed
