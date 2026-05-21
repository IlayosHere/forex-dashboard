"""
runner/gate_runner.py
---------------------
Evaluate the active GateSet for a strategy against a fresh signal.

Signals that fail gate conditions are stored with gate_status="blocked" so
they can be audited and used to tune gate definitions. Discord notifications
are suppressed for blocked signals in runner/main.py.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from analytics.conditions import evaluate_all
from analytics.signal_enricher import ANALYTICS_PARAMS_KEY
from api.models_gates import GateSetModel
from shared.signal import Signal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GateDecision:
    """Result of evaluating gate conditions against a signal."""

    status: str  # "passed" | "blocked" | "no_gates" | "error"
    gate_set_id: str | None
    failed_indices: list[int] = field(default_factory=list)

    @property
    def block_reason(self) -> str | None:
        """Human-readable list of which conditions failed, or None."""
        if not self.failed_indices or self.gate_set_id is None:
            return None
        return ",".join(f"{self.gate_set_id}:{i}" for i in self.failed_indices)


def evaluate_gate_for_signal(db: Session, signal: Signal) -> GateDecision:
    """Look up the active GateSet for signal.strategy and evaluate it.

    Returns a GateDecision with status:
      "no_gates"  — no active gate set defined for this strategy
      "passed"    — all conditions satisfied
      "blocked"   — one or more conditions failed
      "error"     — gate evaluation raised an unexpected exception
    """
    gate_set = _load_active_gate_set(db, signal.strategy)
    if gate_set is None:
        return GateDecision("no_gates", None)

    params = _get_params(signal)
    try:
        passed, failed_indices = evaluate_all(gate_set.conditions, params)
    except Exception:
        logger.exception(
            "Gate evaluation error for signal %s (strategy=%s)",
            signal.id, signal.strategy,
        )
        return GateDecision("error", gate_set.id)

    status = "passed" if passed else "blocked"
    if status == "blocked":
        logger.info(
            "Signal %s %s %s BLOCKED by gate set '%s' — conditions %s failed",
            signal.strategy, signal.symbol, signal.direction,
            gate_set.name, failed_indices,
        )
    return GateDecision(status, gate_set.id, failed_indices)


def _load_active_gate_set(db: Session, strategy: str) -> GateSetModel | None:
    """Return the single active gate set for a strategy, or None."""
    return db.scalar(
        select(GateSetModel).where(
            GateSetModel.strategy == strategy,
            GateSetModel.is_active.is_(True),
        ),
    )


def _get_params(signal: Signal) -> dict[str, Any]:
    """Extract analytics params from signal metadata, defaulting to empty dict."""
    return signal.metadata.get(ANALYTICS_PARAMS_KEY, {})
