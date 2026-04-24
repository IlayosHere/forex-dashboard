"""
tests/test_analytics_interaction.py
-------------------------------------
Tests for the 2D interaction heatmap: grid logic + route endpoint.

Grid logic is tested via build_interaction_grid() directly.
Route tests cover the HTTP contract and the 422 error path.
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
from analytics.stats.interaction import build_interaction_grid
from api.models import SignalModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _enriched(
    signal_id: str,
    resolution: str,
    **params: Any,
) -> dict[str, Any]:
    """Minimal enriched signal dict for grid tests."""
    return {"id": signal_id, "resolution": resolution, "params": params}


def _batch(n_wins: int, n_losses: int, **params: Any) -> list[dict[str, Any]]:
    """Build enriched signals with identical param values."""
    result: list[dict[str, Any]] = []
    for _ in range(n_wins):
        result.append(_enriched(str(uuid.uuid4()), "TP_HIT", **params))
    for _ in range(n_losses):
        result.append(_enriched(str(uuid.uuid4()), "SL_HIT", **params))
    return result


_signal_seq: list[int] = [0]


def _insert_signal(
    db: Session,
    resolution: str = "TP_HIT",
    params: dict[str, Any] | None = None,
) -> SignalModel:
    """Insert a resolved signal with optional stored analytics params.

    Uses a monotonic counter to guarantee unique (strategy, symbol, candle_time).
    """
    from datetime import timedelta

    from analytics.signal_enricher import ANALYTICS_PARAMS_KEY
    meta = {ANALYTICS_PARAMS_KEY: params} if params else {}
    n = _signal_seq[0]
    _signal_seq[0] += 1
    # Use recent dates so fetch_resolved() default 365-day window includes them.
    # Encode n as hour+minute — tests never insert >1440 signals.
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
    """Patch get_candles to return None so no candle-derived params fire."""
    monkeypatch.setattr(cache_mod, "get_candles", lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Unit tests: build_interaction_grid
# ---------------------------------------------------------------------------

def test_interaction_grid_correct_cell_counts() -> None:
    """Grid accumulates wins/losses correctly per (bucket_a, bucket_b) cell."""
    # Create 20 signals spread across two categorical buckets each
    # bucket_a: "A" or "B", bucket_b: "X" or "Y"
    signals: list[dict[str, Any]] = []
    # A+X: 8 wins, 4 losses = 12 (sparse — win_rate None)
    signals += _batch(8, 4, cat_a="A", cat_b="X")
    # A+Y: 10 wins, 5 losses = 15 (not sparse)
    signals += _batch(10, 5, cat_a="A", cat_b="Y")
    # B+X: 12 wins, 6 losses = 18 (not sparse)
    signals += _batch(12, 6, cat_a="B", cat_b="X")
    # B+Y: 9 wins, 9 losses = 18 (not sparse)
    signals += _batch(9, 9, cat_a="B", cat_b="Y")

    _, _, cells = build_interaction_grid(signals, "cat_a", "str", "cat_b", "str")

    by_key = {(c.bucket_a, c.bucket_b): c for c in cells}
    ax = by_key[("A", "X")]
    assert ax.wins == 8
    assert ax.losses == 4
    assert ax.total == 12

    ay = by_key[("A", "Y")]
    assert ay.wins == 10
    assert ay.losses == 5
    assert ay.total == 15

    bx = by_key[("B", "X")]
    assert bx.wins == 12
    assert bx.losses == 6
    assert bx.total == 18

    by = by_key[("B", "Y")]
    assert by.wins == 9
    assert by.losses == 9
    assert by.total == 18


def test_interaction_sparse_cell_has_none_win_rate() -> None:
    """Cell with total < 15 gets win_rate=None; cell with total >= 15 gets a value."""
    signals: list[dict[str, Any]] = []
    signals += _batch(8, 4, cat_a="A", cat_b="X")   # 12 total → sparse
    signals += _batch(10, 5, cat_a="A", cat_b="Y")  # 15 total → not sparse

    _, _, cells = build_interaction_grid(signals, "cat_a", "str", "cat_b", "str")
    by_key = {(c.bucket_a, c.bucket_b): c for c in cells}

    assert by_key[("A", "X")].win_rate is None
    assert by_key[("A", "Y")].win_rate == pytest.approx(10 / 15)


def test_interaction_buckets_ordered_correctly_categorical() -> None:
    """Categorical params produce alphabetically sorted bucket lists."""
    signals: list[dict[str, Any]] = []
    signals += _batch(5, 5, cat_a="Z", cat_b="B")
    signals += _batch(5, 5, cat_a="A", cat_b="C")

    ordered_a, ordered_b, _ = build_interaction_grid(
        signals, "cat_a", "str", "cat_b", "str",
    )
    assert ordered_a == sorted(ordered_a)
    assert ordered_b == sorted(ordered_b)


def test_interaction_buckets_ordered_correctly_numeric() -> None:
    """Numeric params produce Q1-before-Q5 ordered buckets."""
    # 50 signals with values 1..50 spread as wins/losses
    signals: list[dict[str, Any]] = []
    for i in range(1, 51):
        signals.append(_enriched(
            str(uuid.uuid4()),
            "TP_HIT" if i % 2 == 0 else "SL_HIT",
            num_a=float(i),
            cat_b="X",
        ))

    ordered_a, _, _ = build_interaction_grid(
        signals, "num_a", "float", "cat_b", "str",
    )
    # Each label starts with Q{n}
    q_nums = [int(label[1]) for label in ordered_a if label.startswith("Q")]
    assert q_nums == sorted(q_nums)
    assert q_nums[0] == 1


# ---------------------------------------------------------------------------
# Route tests: GET /api/analytics/interaction
# ---------------------------------------------------------------------------

def test_interaction_invalid_param_a_returns_422(
    client: TestClient,
    db: Session,
    no_candles: None,
) -> None:
    """Unregistered param_a must return 422."""
    _insert_signal(db, "TP_HIT", {"session_label": "LONDON"})
    res = client.get(
        "/api/analytics/interaction"
        "?strategy=fvg-impulse&param_a=nonexistent_xyz&param_b=session_label",
    )
    assert res.status_code == 422
    assert "nonexistent_xyz" in res.json()["detail"]


def test_interaction_invalid_param_b_returns_422(
    client: TestClient,
    db: Session,
    no_candles: None,
) -> None:
    """Unregistered param_b must return 422."""
    _insert_signal(db, "TP_HIT", {"session_label": "LONDON"})
    res = client.get(
        "/api/analytics/interaction"
        "?strategy=fvg-impulse&param_a=session_label&param_b=nonexistent_xyz",
    )
    assert res.status_code == 422
    assert "nonexistent_xyz" in res.json()["detail"]


def test_interaction_route_returns_valid_response(
    client: TestClient,
    db: Session,
    no_candles: None,
) -> None:
    """Valid request returns correct schema with total_signals and overall_win_rate."""
    for _ in range(10):
        _insert_signal(db, "TP_HIT", {"session_label": "LONDON", "hour_bucket": "H1"})
    for _ in range(10):
        _insert_signal(db, "SL_HIT", {"session_label": "NY_OVERLAP", "hour_bucket": "H2"})

    res = client.get(
        "/api/analytics/interaction"
        "?strategy=fvg-impulse&param_a=session_label&param_b=hour_bucket",
    )
    assert res.status_code == 200
    body = res.json()

    assert body["strategy"] == "fvg-impulse"
    assert body["param_a"] == "session_label"
    assert body["param_b"] == "hour_bucket"
    assert body["total_signals"] == 20
    assert body["overall_win_rate"] == pytest.approx(0.5)
    assert isinstance(body["buckets_a"], list)
    assert isinstance(body["buckets_b"], list)
    assert isinstance(body["cells"], list)
    for cell in body["cells"]:
        assert "bucket_a" in cell
        assert "bucket_b" in cell
        assert "wins" in cell
        assert "losses" in cell
        assert "total" in cell
