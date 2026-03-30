"""
shared/notifier
---------------
Strategy-aware Discord embed builder. Pure formatting — no I/O.

Public API
----------
build_embed(sig: Signal) -> dict
    Dispatches to the registered embed builder for sig.strategy.
    Falls back to a generic embed for unknown strategies.
"""
from shared.notifier._registry import build_embed

__all__ = ["build_embed"]
