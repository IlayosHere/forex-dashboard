"""
tests/test_analytics_combinations.py
--------------------------------------
Unit tests for analytics/stats/combinations.py and
GET /api/analytics/top-combinations route.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import analytics.params  # noqa: F401 — trigger param registration
import api.main as main_mod
from analytics import candle_cache as cache_mod
from analytics.routes_stats import _enriched_cache, _enriched_lock
from analytics.stats.combinations import (
    _bonferroni_z,
    find_top_combinations,
)
from analytics.stats.univariate import wilson_ci
from api.models import SignalModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sig(resolution: str, **params: Any) -> dict[str, Any]:
    """Minimal enriched signal dict with a unique id."""
    return {"id": str(uuid.uuid4()), "resolution": resolution, "params": params}


def _batch(n_wins: int, n_losses: int, **params: Any) -> list[dict[str, Any]]:
    """Build enriched signal batch with identical param values."""
    signals: list[dict[str, Any]] = []
    for _ in range(n_wins):
        signals.append(_sig("TP_HIT", **params))
    for _ in range(n_losses):
        signals.append(_sig("SL_HIT", **params))
    return signals


_seq: list[int] = [0]


def _insert_signal(
    db: Session,
    resolution: str = "TP_HIT",
    params: dict[str, Any] | None = None,
) -> SignalModel:
    """Insert a resolved signal into the test DB."""
    from datetime import timedelta
    from analytics.signal_enricher import ANALYTICS_PARAMS_KEY

    meta = {ANALYTICS_PARAMS_KEY: params} if params else {}
    n = _seq[0]
    _seq[0] += 1
    hour = (n // 60) % 24
    minute = n % 60
    base = datetime(2026, 3, 1, tzinfo=timezone.utc)
    candle_time = base + timedelta(hours=hour, minutes=minute)
    sig = SignalModel(
        id=str(uuid.uuid4()),
        strategy="fvg-impulse",
        symbol="EURUSD",
        direction="BUY",
        candle_time=candle_time,
        entry=1.08500,
        sl=1.08200,
        tp=1.09100,
        lot_size=0.5,
        risk_pips=30.0,
        spread_pips=1.0,
        signal_metadata=meta,
        created_at=datetime.now(timezone.utc),
        resolution=resolution,
        resolved_at=datetime.now(timezone.utc),
        resolved_price=1.08800,
        resolution_candles=5,
    )
    db.add(sig)
    db.commit()
    db.refresh(sig)
    return sig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Clear enriched-signal cache and disable prewarm loop."""
    async def _noop() -> None:  # pragma: no cover
        pass

    monkeypatch.setattr(main_mod, "_prewarm_loop", _noop)
    cache_mod._app_cache = None
    with _enriched_lock:
        _enriched_cache.clear()
    yield
    cache_mod._app_cache = None
    with _enriched_lock:
        _enriched_cache.clear()


@pytest.fixture()
def no_candles(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch get_candles to return None so candle-derived params do not fire."""
    monkeypatch.setattr(cache_mod, "get_candles", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# wilson_ci rename smoke test
# ---------------------------------------------------------------------------

def test_wilson_ci_public_import() -> None:
    """wilson_ci is importable from analytics.stats.univariate (no leading underscore)."""
    lo, hi = wilson_ci(50, 100)
    assert 0.0 <= lo < hi <= 1.0


def test_wilson_ci_zero_total() -> None:
    """wilson_ci returns (0.0, 0.0) for zero total."""
    assert wilson_ci(0, 0) == (0.0, 0.0)


# ---------------------------------------------------------------------------
# _bonferroni_z
# ---------------------------------------------------------------------------

def test_bonferroni_z_single_test_equals_standard() -> None:
    """With k=1, adjusted z equals standard 1.96."""
    z = _bonferroni_z(1)
    assert z == pytest.approx(1.96, abs=0.01)


def test_bonferroni_z_increases_with_k() -> None:
    """Bonferroni z must increase as k increases (stricter threshold)."""
    z1 = _bonferroni_z(1)
    z10 = _bonferroni_z(10)
    z100 = _bonferroni_z(100)
    assert z1 < z10 < z100


def test_bonferroni_z_capped_at_max_k() -> None:
    """k values beyond MAX_BONFERRONI_K=200 are clamped — z stays finite."""
    z = _bonferroni_z(9999)
    z_max = _bonferroni_z(200)
    assert z == pytest.approx(z_max, abs=1e-9)


# ---------------------------------------------------------------------------
# find_top_combinations — unit tests (no DB, no HTTP)
# ---------------------------------------------------------------------------

def test_find_top_combinations_insufficient_params() -> None:
    """Fewer than 2 confirmed params returns reason=insufficient_confirmed_params."""
    result = find_top_combinations(
        enriched=[],
        confirmed_params=[{"name": "session_label", "dtype": "str"}],
        overall_win_rate=0.5,
    )
    assert result["reason"] == "insufficient_confirmed_params"
    assert result["items"] == []
    assert result["pairs_scanned"] == 0


def test_find_top_combinations_no_params_at_all() -> None:
    """Zero confirmed params also returns insufficient_confirmed_params."""
    result = find_top_combinations(
        enriched=[],
        confirmed_params=[],
        overall_win_rate=0.5,
    )
    assert result["reason"] == "insufficient_confirmed_params"


def test_find_top_combinations_finds_positive_edge() -> None:
    """Returns a positive-edge combination when one cell clearly beats baseline."""
    # baseline ~50%: 50 wins, 50 losses mixed across all buckets
    # high-edge cell: cat_a=A + cat_b=X → 30 wins, 2 losses = 93.7% >> 50%
    signals: list[dict[str, Any]] = []
    signals += _batch(30, 2, cat_a="A", cat_b="X")   # strong positive cell
    signals += _batch(20, 48, cat_a="B", cat_b="Y")  # drag to keep baseline near 50%

    confirmed = [
        {"name": "cat_a", "dtype": "str"},
        {"name": "cat_b", "dtype": "str"},
    ]
    overall_wr = 50 / 100  # 50 wins / 100 total

    result = find_top_combinations(
        enriched=signals,
        confirmed_params=confirmed,
        overall_win_rate=overall_wr,
        min_cell_n=25,
    )

    assert result["reason"] is None
    assert len(result["items"]) >= 1
    top = result["items"][0]
    assert top["rank"] == 1
    assert top["direction"] == "positive"
    assert top["param_a"] in ("cat_a", "cat_b")
    assert top["param_b"] in ("cat_a", "cat_b")
    assert top["win_rate"] > overall_wr + 0.02
    assert top["score"] > 0.0


def test_find_top_combinations_no_edge_found() -> None:
    """Returns reason=no_edge_found when no cell passes the threshold."""
    # All cells have win rate near 50% — no edge
    signals = _batch(25, 25, cat_a="A", cat_b="X")

    confirmed = [
        {"name": "cat_a", "dtype": "str"},
        {"name": "cat_b", "dtype": "str"},
    ]

    result = find_top_combinations(
        enriched=signals,
        confirmed_params=confirmed,
        overall_win_rate=0.5,
        min_cell_n=25,
    )

    assert result["reason"] == "no_edge_found"
    assert result["items"] == []


def test_find_top_combinations_respects_limit() -> None:
    """Result list is capped at the limit parameter."""
    # Build many positive-edge cells across multiple param pairs
    confirmed_params = [
        {"name": f"cat_{i}", "dtype": "str"} for i in range(5)
    ]
    signals: list[dict[str, Any]] = []
    # Each combo (cat_0=A + cat_i=A) has strong positive signal
    for i in range(1, 5):
        signals += _batch(30, 1, **{f"cat_0": "A", f"cat_{i}": "A"})
        signals += _batch(1, 10, **{f"cat_0": "B", f"cat_{i}": "B"})

    result = find_top_combinations(
        enriched=signals,
        confirmed_params=confirmed_params,
        overall_win_rate=0.5,
        limit=2,
        min_cell_n=25,
    )

    assert len(result["items"]) <= 2


def test_find_top_combinations_rank_is_one_based() -> None:
    """Rank field is 1-based and sequential."""
    signals: list[dict[str, Any]] = []
    signals += _batch(30, 2, cat_a="A", cat_b="X")
    signals += _batch(20, 48, cat_a="B", cat_b="Y")

    confirmed = [
        {"name": "cat_a", "dtype": "str"},
        {"name": "cat_b", "dtype": "str"},
    ]

    result = find_top_combinations(
        enriched=signals,
        confirmed_params=confirmed,
        overall_win_rate=0.5,
        min_cell_n=25,
    )

    if result["items"]:
        ranks = [item["rank"] for item in result["items"]]
        assert ranks[0] == 1
        assert ranks == list(range(1, len(ranks) + 1))


def test_find_top_combinations_items_have_required_fields() -> None:
    """Every returned item contains all required TopCombination fields."""
    signals: list[dict[str, Any]] = []
    signals += _batch(30, 2, cat_a="A", cat_b="X")
    signals += _batch(5, 20, cat_a="B", cat_b="Y")

    confirmed = [
        {"name": "cat_a", "dtype": "str"},
        {"name": "cat_b", "dtype": "str"},
    ]

    result = find_top_combinations(
        enriched=signals,
        confirmed_params=confirmed,
        overall_win_rate=0.5,
        min_cell_n=25,
    )

    required_fields = {
        "rank", "param_a", "bucket_a", "param_b", "bucket_b",
        "wins", "losses", "total", "win_rate", "edge", "direction",
        "ci_lo_raw", "ci_hi_raw", "ci_lo_adjusted", "ci_hi_adjusted", "score",
    }

    for item in result["items"]:
        missing = required_fields - set(item.keys())
        assert not missing, f"Item missing fields: {missing}"


# ---------------------------------------------------------------------------
# GET /api/analytics/top-combinations — route tests
# ---------------------------------------------------------------------------

def test_top_combinations_missing_strategy_returns_422(
    client: TestClient,
    no_candles: None,
) -> None:
    """Omitting strategy query param must return 422."""
    res = client.get("/api/analytics/top-combinations")
    assert res.status_code == 422


def test_top_combinations_empty_db_returns_insufficient(
    client: TestClient,
    db: Session,
    no_candles: None,
) -> None:
    """With no resolved signals, confirmed_param_count is 0 → insufficient reason."""
    res = client.get("/api/analytics/top-combinations?strategy=fvg-impulse")
    assert res.status_code == 200
    body = res.json()
    assert body["strategy"] == "fvg-impulse"
    assert body["reason"] in ("insufficient_confirmed_params", "no_edge_found")
    assert body["items"] == []


def test_top_combinations_response_schema(
    client: TestClient,
    db: Session,
    no_candles: None,
) -> None:
    """Response always contains all required top-level schema fields."""
    for _ in range(5):
        _insert_signal(db, "TP_HIT", {"session_label": "LONDON"})
    for _ in range(5):
        _insert_signal(db, "SL_HIT", {"session_label": "NY_OVERLAP"})

    res = client.get("/api/analytics/top-combinations?strategy=fvg-impulse")
    assert res.status_code == 200
    body = res.json()

    required = {
        "strategy", "total_signals", "overall_win_rate",
        "confirmed_param_count", "pairs_scanned", "cells_evaluated",
        "items", "reason",
    }
    missing = required - set(body.keys())
    assert not missing, f"Response missing fields: {missing}"
    assert isinstance(body["items"], list)


def test_top_combinations_limit_param_respected(
    client: TestClient,
    db: Session,
    no_candles: None,
) -> None:
    """The limit query param is accepted and caps result length."""
    res = client.get(
        "/api/analytics/top-combinations?strategy=fvg-impulse&limit=3",
    )
    assert res.status_code == 200
    body = res.json()
    assert len(body["items"]) <= 3


def test_top_combinations_limit_out_of_range_returns_422(
    client: TestClient,
    no_candles: None,
) -> None:
    """limit=0 is below the minimum (ge=1) and must return 422."""
    res = client.get(
        "/api/analytics/top-combinations?strategy=fvg-impulse&limit=0",
    )
    assert res.status_code == 422
