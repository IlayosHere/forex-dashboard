"""
shared/notifier/_registry.py
-----------------------------
Strategy embed builder registry, @register decorator, and dispatch function.

Adding a new strategy
---------------------
1. Create shared/notifier/_<slug>.py with a @register("<slug>") function.
2. Add one import at the bottom of this file to trigger registration.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from shared.notifier._base import EmbedBuilder, embed_base
from shared.signal import Signal

logger = logging.getLogger(__name__)

_BUILDERS: dict[str, EmbedBuilder] = {}


def register(strategy_slug: str) -> Callable[[EmbedBuilder], EmbedBuilder]:
    """Decorator that registers an embed builder for a strategy slug.

    Parameters
    ----------
    strategy_slug : str
        The hyphen-slug that matches Signal.strategy, e.g. "fvg-impulse".

    Returns
    -------
    Callable
        Decorator that stores the function in _BUILDERS and returns it unchanged.
    """
    def decorator(fn: EmbedBuilder) -> EmbedBuilder:
        _BUILDERS[strategy_slug] = fn
        return fn
    return decorator


def build_embed(sig: Signal) -> dict:
    """Dispatch to the registered embed builder for sig.strategy.

    Falls back to _generic_embed if no builder is registered.

    Parameters
    ----------
    sig : Signal
        Signal to build a Discord embed for.

    Returns
    -------
    dict
        Discord embed dict ready for POSTing to a webhook.
    """
    builder = _BUILDERS.get(sig.strategy, _generic_embed)
    return builder(sig)


def _generic_embed(sig: Signal) -> dict:
    label = sig.strategy.replace("-", " ").title()
    logger.warning(
        "No embed builder for strategy '%s' -- using generic embed", sig.strategy,
    )
    return embed_base(
        sig,
        title=f"[{label}] {sig.direction} Signal: {sig.symbol}",
        description=f"New signal on {TIMEFRAME_LABEL}",
    )


# ---------------------------------------------------------------------------
# Trigger builder registrations.
# Every supported strategy must have one import line here.
# To add a new strategy: create shared/notifier/_<slug>.py and add it below.
# ---------------------------------------------------------------------------

TIMEFRAME_LABEL = "M15"  # used by _generic_embed

from shared.notifier import _fvg_impulse  # noqa: E402, F401
from shared.notifier import _nova_candle  # noqa: E402, F401
