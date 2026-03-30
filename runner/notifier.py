"""
runner/notifier.py
------------------
HTTP delivery layer for Discord alerts.

Resolves the webhook URL per strategy (per-strategy override or global
fallback) and POSTs pre-built embed dicts from shared.notifier.

Webhook URL resolution
----------------------
For a signal with strategy="fvg-impulse", the lookup order is:
  1. FVG_IMPULSE_WEBHOOK_URL  (per-strategy override)
  2. DISCORD_WEBHOOK_URL      (global fallback)

To add a dedicated channel for a strategy, set its env var and leave
DISCORD_WEBHOOK_URL as the catch-all for everything else.
"""
from __future__ import annotations

import logging
import os

import requests

from shared.notifier import build_embed
from shared.signal import Signal

logger = logging.getLogger(__name__)


def _resolve_webhook(strategy: str) -> str:
    """Return the Discord webhook URL for a strategy.

    Checks for a per-strategy override before falling back to the global URL.

    Parameters
    ----------
    strategy : str
        Strategy slug, e.g. "fvg-impulse".

    Returns
    -------
    str
        Webhook URL, or empty string if none is configured.
    """
    env_key = strategy.replace("-", "_").upper() + "_WEBHOOK_URL"
    return os.getenv(env_key) or os.getenv("DISCORD_WEBHOOK_URL", "")


def _post_embed(webhook_url: str, embed: dict, label: str) -> None:
    """POST a single embed dict to a Discord webhook. Logs on failure."""
    try:
        resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=5)
        if resp.status_code in (200, 204):
            logger.debug("Discord alert sent: %s", label)
        else:
            logger.warning(
                "Discord webhook returned %d for %s: %s",
                resp.status_code, label, resp.text[:200],
            )
    except Exception:
        logger.exception("Failed to send Discord alert for %s", label)


def send_signals(signals: list[Signal]) -> None:
    """Send Discord alerts for a list of Signal objects.

    Dispatches each Signal to its registered embed builder, resolves the
    webhook URL (per-strategy override or global fallback), and POSTs each
    embed as a separate webhook message. Best-effort: errors are logged
    and never raised.

    Parameters
    ----------
    signals : list[Signal]
        Signals to notify. Empty list is a no-op.
    """
    for sig in signals:
        webhook_url = _resolve_webhook(sig.strategy)
        if not webhook_url:
            logger.warning(
                "No webhook URL configured for strategy '%s' -- skipping alert",
                sig.strategy,
            )
            continue
        embed = build_embed(sig)
        label = f"{sig.strategy} {sig.symbol} {sig.direction}"
        _post_embed(webhook_url, embed, label)
