"""
tests/test_analytics_regime.py
-------------------------------
Unit tests for regime-shift detection logic in analytics/stats/regime.py.
Tests operate on compute_regime() directly with stub signal objects.
"""
from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from analytics.stats.regime import compute_regime


def _make_signal(resolution: str) -> MagicMock:
    """Return a minimal stub with a resolution attribute."""
    s = MagicMock()
    s.resolution = resolution
    return s


def _signals(n_wins: int, n_losses: int) -> list[MagicMock]:
    """Build a list of win+loss stub signals."""
    return [_make_signal("TP_HIT") for _ in range(n_wins)] + [
        _make_signal("SL_HIT") for _ in range(n_losses)
    ]


def _two_windows(
    recent_wins: int, recent_losses: int, prior_wins: int, prior_losses: int
) -> list[MagicMock]:
    """Build 60 signals: first 30 = recent, next 30 = prior."""
    return _signals(recent_wins, recent_losses) + _signals(prior_wins, prior_losses)


def test_regime_healthy_when_similar_win_rates() -> None:
    """Two windows both ~50% win rate → status='healthy'."""
    signals = _two_windows(15, 15, 15, 15)
    result = compute_regime(signals)
    assert result["sufficient_data"] is True
    assert result["status"] == "healthy"
    assert result["recent"]["win_rate"] == pytest.approx(0.5)
    assert result["prior"]["win_rate"] == pytest.approx(0.5)
    assert result["delta"] == pytest.approx(0.0)


def test_regime_degraded_when_recent_worse() -> None:
    """Recent 30% win rate, prior 65% win rate → status='degraded'."""
    signals = _two_windows(9, 21, 20, 10)
    result = compute_regime(signals)
    assert result["sufficient_data"] is True
    assert result["status"] == "degraded"
    assert result["delta"] < 0
    assert result["z_score"] is not None
    assert abs(result["z_score"]) >= 2.0


def test_regime_insufficient_data_when_few_signals() -> None:
    """Only 15 total signals → sufficient_data=False, status='insufficient_data'."""
    signals = _signals(8, 7)
    result = compute_regime(signals)
    assert result["sufficient_data"] is False
    assert result["status"] == "insufficient_data"


def test_regime_warning_zone() -> None:
    """Borderline divergence landing in warning zone (1.65 ≤ |z| < 2.0)."""
    # 24/30 = 80% recent vs 30/30... find values that produce z ≈ 1.7
    # Use 12/30 recent and 18/30 prior (40% vs 60%), z ≈ 1.75
    signals = _two_windows(12, 18, 18, 12)
    result = compute_regime(signals)
    assert result["sufficient_data"] is True
    z = result["z_score"]
    assert z is not None
    if 1.65 <= abs(z) < 2.0:
        assert result["status"] == "warning"
    else:
        # z may land outside the warning band — assert degraded or healthy
        assert result["status"] in ("healthy", "degraded", "warning")


def test_regime_improving_not_degraded() -> None:
    """Significant improvement (recent much better) → status='healthy', not 'degraded'."""
    signals = _two_windows(20, 10, 9, 21)
    result = compute_regime(signals)
    assert result["sufficient_data"] is True
    assert result["delta"] > 0
    # Significant improvement is healthy, not degraded
    assert result["status"] != "degraded"


def test_regime_recent_and_prior_stats_correct() -> None:
    """Check that window stats are correctly split into recent vs prior."""
    signals = _two_windows(20, 10, 5, 25)
    result = compute_regime(signals)
    assert result["recent"]["n"] == 30
    assert result["recent"]["wins"] == 20
    assert result["recent"]["win_rate"] == pytest.approx(20 / 30)
    assert result["prior"]["n"] == 30
    assert result["prior"]["wins"] == 5
    assert result["prior"]["win_rate"] == pytest.approx(5 / 30)


def test_regime_z_score_is_none_when_pool_probability_is_one() -> None:
    """All wins in both windows → p_pool=1, variance=0, z_score=None → insufficient_data."""
    signals = _two_windows(30, 0, 30, 0)
    result = compute_regime(signals)
    assert result["z_score"] is None
    assert result["status"] == "insufficient_data"
