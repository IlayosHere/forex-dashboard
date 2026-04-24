"""
analytics/stats/regime.py
-------------------------
Regime-shift detection: compare last 30 vs prior 30 resolved signals.
"""
from __future__ import annotations

import math

from api.models import SignalModel


_WINDOW_SIZE = 30
_MIN_WINDOW = 20
_MIN_TOTAL = 40


def _window_stats(signals: list[SignalModel]) -> tuple[int, int, float]:
    """Return (n, wins, win_rate) for a list of signals."""
    n = len(signals)
    wins = sum(1 for s in signals if s.resolution == "TP_HIT")
    win_rate = wins / n if n > 0 else 0.0
    return n, wins, win_rate


def _two_proportion_z(w1: int, n1: int, w2: int, n2: int) -> float | None:
    """Compute two-proportion z-score. Returns None if denominator is zero."""
    p1 = w1 / n1
    p2 = w2 / n2
    p_pool = (w1 + w2) / (n1 + n2)
    variance = p_pool * (1 - p_pool) * (1 / n1 + 1 / n2)
    if variance <= 0:
        return None
    return (p1 - p2) / math.sqrt(variance)


def _classify_status(z: float | None, delta: float, sufficient: bool) -> str:
    """Map z-score and delta to a status string."""
    if not sufficient:
        return "insufficient_data"
    if z is None:
        return "insufficient_data"
    abs_z = abs(z)
    if abs_z < 1.65:
        return "healthy"
    if abs_z < 2.0:
        return "warning"
    return "degraded" if delta < 0 else "healthy"


def compute_regime(
    signals: list[SignalModel],
) -> dict:
    """Compute regime shift stats from the 60 most-recent resolved signals.

    Parameters
    ----------
    signals : list[SignalModel]
        Up to 60 resolved signals, ordered most-recent first.

    Returns
    -------
    dict matching RegimeResponse fields (excluding strategy/symbol).
    """
    total = len(signals)
    sufficient_data = total >= _MIN_TOTAL

    recent_signals = signals[:_WINDOW_SIZE]
    prior_signals = signals[_WINDOW_SIZE:_WINDOW_SIZE * 2]

    n_recent, w_recent, wr_recent = _window_stats(recent_signals)
    n_prior, w_prior, wr_prior = _window_stats(prior_signals)

    both_sufficient = n_recent >= _MIN_WINDOW and n_prior >= _MIN_WINDOW
    sufficient_data = sufficient_data and both_sufficient

    delta = wr_recent - wr_prior
    z_score: float | None = None
    if sufficient_data and n_recent > 0 and n_prior > 0:
        z_score = _two_proportion_z(w_recent, n_recent, w_prior, n_prior)

    status = _classify_status(z_score, delta, sufficient_data)

    return {
        "recent": {"n": n_recent, "wins": w_recent, "win_rate": wr_recent},
        "prior": {"n": n_prior, "wins": w_prior, "win_rate": wr_prior},
        "delta": delta,
        "z_score": z_score,
        "status": status,
        "sufficient_data": sufficient_data,
    }
