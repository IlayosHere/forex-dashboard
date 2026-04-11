"""
tests/test_analytics_routes_tf.py
----------------------------------
Route-level tests verifying the analytics endpoints wire a timeframe-aware
``CandleCache`` through ``enrich_with_candles`` — the fix that turned the
TF refactor on at runtime.

Covers:
  - /api/analytics/enriched
  - /api/analytics/univariate/{param_name}
  - /api/analytics/summary

Every test patches ``shared.market_data.get_candles`` (via the
``analytics.candle_cache.get_candles`` import) so no network I/O occurs and
we can observe exactly which ``(symbol, interval)`` pairs were fetched and
force-fail specific ones to verify graceful degradation.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from tvDatafeed import Interval

import analytics.params  # noqa: F401 — trigger param registration
from analytics import candle_cache as cache_mod
from api.models import SignalModel


FetchCall = tuple[str, Interval, int]


def _make_df(n: int = 300, base: float = 1.08) -> pd.DataFrame:
    """Deterministic M15 OHLC frame large enough for candle-derived params."""
    idx = pd.date_range(
        "2025-03-10 00:00", periods=n, freq="15min", tz="UTC",
    )
    return pd.DataFrame(
        {
            "open":  [base + i * 0.0001 for i in range(n)],
            "high":  [base + i * 0.0001 + 0.0010 for i in range(n)],
            "low":   [base + i * 0.0001 - 0.0005 for i in range(n)],
            "close": [base + i * 0.0001 + 0.0003 for i in range(n)],
        },
        index=idx,
    )


def _insert_resolved_signal(
    db: Session,
    *,
    symbol: str = "EURUSD",
    strategy: str = "fvg-impulse",
    resolution: str = "TP_HIT",
    candle_hour: int = 10,
) -> SignalModel:
    """Insert a TP/SL-resolved signal aligned on the deterministic fixture."""
    sig = SignalModel(
        id=str(uuid.uuid4()),
        strategy=strategy,
        symbol=symbol,
        direction="BUY",
        candle_time=datetime(2025, 3, 11, candle_hour, 0, tzinfo=timezone.utc),
        entry=1.08500,
        sl=1.08200,
        tp=1.08800,
        lot_size=0.5,
        risk_pips=30.0,
        spread_pips=1.0,
        signal_metadata={"fvg_age": 3, "fvg_width_pips": 4.5},
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


@pytest.fixture(autouse=True)
def _reset_app_cache() -> None:
    """Reset the app-scoped CandleCache singleton between tests.

    Without this, cache entries from one test leak into the next and fetch
    counts become non-deterministic.
    """
    cache_mod._APP_CACHE = None
    yield
    cache_mod._APP_CACHE = None


@pytest.fixture()
def fetch_recorder(
    monkeypatch: pytest.MonkeyPatch,
) -> list[FetchCall]:
    """Patch ``get_candles`` in candle_cache; record every call."""
    calls: list[FetchCall] = []

    def fake_get_candles(
        symbol: str, interval: Interval, count: int = 300,
    ) -> pd.DataFrame:
        calls.append((symbol, interval, count))
        return _make_df(n=300)

    monkeypatch.setattr(cache_mod, "get_candles", fake_get_candles)
    return calls


@pytest.fixture()
def fetch_failing(
    monkeypatch: pytest.MonkeyPatch,
) -> list[FetchCall]:
    """Patch ``get_candles`` so one symbol fails (returns None)."""
    calls: list[FetchCall] = []

    def fake_get_candles(
        symbol: str, interval: Interval, count: int = 300,
    ) -> pd.DataFrame | None:
        calls.append((symbol, interval, count))
        if symbol == "GBPUSD":
            return None  # simulate tvDatafeed down / unknown pair
        return _make_df(n=300)

    monkeypatch.setattr(cache_mod, "get_candles", fake_get_candles)
    return calls


# ---------------------------------------------------------------------------
# /api/analytics/enriched
# ---------------------------------------------------------------------------


def test_enriched_route_warms_cache_with_unique_pairs(
    client: TestClient,
    db: Session,
    fetch_recorder: list[FetchCall],
) -> None:
    """Route should warm the cache once per (symbol, strategy) pair."""
    _insert_resolved_signal(db, symbol="EURUSD", candle_hour=10)
    _insert_resolved_signal(db, symbol="EURUSD", candle_hour=11)  # dup pair
    _insert_resolved_signal(db, symbol="USDJPY", candle_hour=12)

    res = client.get("/api/analytics/enriched?strategy=fvg-impulse")
    assert res.status_code == 200

    fetched_keys = {(sym, iv) for sym, iv, _ in fetch_recorder}
    assert ("EURUSD", Interval.in_15_minute) in fetched_keys
    assert ("USDJPY", Interval.in_15_minute) in fetched_keys
    # Dedup: EURUSD fetched exactly once, not per-signal
    eurusd_calls = [c for c in fetch_recorder if c[0] == "EURUSD"]
    assert len(eurusd_calls) == 1


def test_enriched_route_uses_strategy_interval(
    client: TestClient,
    db: Session,
    fetch_recorder: list[FetchCall],
) -> None:
    """M5 strategy must fetch at Interval.in_5_minute, not M15."""
    _insert_resolved_signal(
        db, symbol="EURUSD", strategy="fvg-impulse-5m", candle_hour=10,
    )

    res = client.get("/api/analytics/enriched?strategy=fvg-impulse-5m")
    assert res.status_code == 200

    intervals = {iv for _, iv, _ in fetch_recorder}
    assert Interval.in_5_minute in intervals
    assert Interval.in_15_minute not in intervals


def test_enriched_route_graceful_on_fetch_failure(
    client: TestClient,
    db: Session,
    fetch_failing: list[FetchCall],
) -> None:
    """A symbol returning None candles must not 500 the request.

    Candle-dependent params are skipped for the failed symbol; the response
    still ships with every signal present.
    """
    _insert_resolved_signal(db, symbol="EURUSD", candle_hour=10)
    _insert_resolved_signal(db, symbol="GBPUSD", candle_hour=11)  # will fail

    res = client.get("/api/analytics/enriched?strategy=fvg-impulse")
    assert res.status_code == 200

    body = res.json()
    items_by_symbol: dict[str, dict[str, Any]] = {
        item["symbol"]: item for item in body["items"]
    }
    assert set(items_by_symbol.keys()) == {"EURUSD", "GBPUSD"}

    # EURUSD succeeded → candle-dependent param present and non-None
    eurusd_params = items_by_symbol["EURUSD"]["params"]
    assert eurusd_params.get("atr_14") is not None

    # GBPUSD failed → candle-dependent params are either missing or None,
    # but the signal still made it into the response
    gbp_params = items_by_symbol["GBPUSD"]["params"]
    assert gbp_params.get("atr_14") is None  # skipped → .get returns None


# ---------------------------------------------------------------------------
# /api/analytics/univariate/{param_name}
# ---------------------------------------------------------------------------


def test_univariate_route_warms_cache(
    client: TestClient,
    db: Session,
    fetch_recorder: list[FetchCall],
) -> None:
    """Univariate endpoint must warm the cache before enriching."""
    _insert_resolved_signal(db, symbol="EURUSD", resolution="TP_HIT")
    _insert_resolved_signal(
        db, symbol="EURUSD", resolution="SL_HIT", candle_hour=12,
    )

    res = client.get(
        "/api/analytics/univariate/session_label?strategy=fvg-impulse",
    )
    assert res.status_code == 200

    # Even for a non-candle param like session_label the route still warms
    # the cache — the cache is built up-front from the signal set.
    assert any(sym == "EURUSD" for sym, _, _ in fetch_recorder)


def test_univariate_route_graceful_on_fetch_failure(
    client: TestClient,
    db: Session,
    fetch_failing: list[FetchCall],
) -> None:
    """Fetch failure must not 500 the univariate endpoint."""
    _insert_resolved_signal(db, symbol="EURUSD", resolution="TP_HIT")
    _insert_resolved_signal(
        db, symbol="GBPUSD", resolution="SL_HIT", candle_hour=12,
    )

    res = client.get(
        "/api/analytics/univariate/session_label?strategy=fvg-impulse",
    )
    assert res.status_code == 200
    body = res.json()
    assert body["param_name"] == "session_label"
    assert body["total_signals"] == 2


# ---------------------------------------------------------------------------
# /api/analytics/summary
# ---------------------------------------------------------------------------


def test_summary_route_does_not_warm_cache(
    client: TestClient,
    db: Session,
    fetch_recorder: list[FetchCall],
) -> None:
    """Summary endpoint intentionally skips cache warming to avoid blocking
    the landing page (~14 s cold-cache penalty). It uses candle_cache=None
    so no get_candles calls should be made for the summary route.
    """
    _insert_resolved_signal(db, symbol="EURUSD", resolution="TP_HIT")
    _insert_resolved_signal(
        db, symbol="USDJPY", resolution="SL_HIT", candle_hour=12,
    )

    res = client.get("/api/analytics/summary?strategy=fvg-impulse")
    assert res.status_code == 200
    body = res.json()
    assert body["total_resolved"] == 2
    # No network fetches for the summary route.
    assert len(fetch_recorder) == 0


def test_summary_route_graceful_on_fetch_failure(
    client: TestClient,
    db: Session,
    fetch_failing: list[FetchCall],
) -> None:
    """Fetch failure must not 500 the summary endpoint."""
    _insert_resolved_signal(db, symbol="EURUSD", resolution="TP_HIT")
    _insert_resolved_signal(
        db, symbol="GBPUSD", resolution="SL_HIT", candle_hour=12,
    )

    res = client.get("/api/analytics/summary?strategy=fvg-impulse")
    assert res.status_code == 200
    body = res.json()
    assert body["strategy"] == "fvg-impulse"
    assert body["total_resolved"] == 2


# ---------------------------------------------------------------------------
# Edge cases: unknown param, empty strategy
# ---------------------------------------------------------------------------


def test_univariate_route_returns_404_for_unknown_param(
    client: TestClient,
    db: Session,
    fetch_recorder: list[FetchCall],
) -> None:
    """Requesting an unregistered param name must return 404, not 500."""
    _insert_resolved_signal(db, symbol="EURUSD", resolution="TP_HIT")

    res = client.get(
        "/api/analytics/univariate/nonexistent_param_xyz?strategy=fvg-impulse",
    )
    assert res.status_code == 404
    assert "nonexistent_param_xyz" in res.json()["detail"]


def test_summary_route_empty_strategy_returns_zero_signals(
    client: TestClient,
    db: Session,
    fetch_recorder: list[FetchCall],
) -> None:
    """Summary for a strategy with 0 resolved signals must return a valid
    response, not a 500. total_resolved is 0; params_analyzed reflects the
    number of registered params (not the number with data)."""
    # No signals inserted — DB is empty for this strategy.
    res = client.get("/api/analytics/summary?strategy=fvg-impulse")
    assert res.status_code == 200
    body = res.json()
    assert body["strategy"] == "fvg-impulse"
    assert body["total_resolved"] == 0
    assert body["win_rate_overall"] == 0.0
    # params_analyzed = number of registered params, not 0 even when no signals.
    assert body["params_analyzed"] > 0
    # All correlations have null significance — no signals to compute from.
    for c in body["top_correlations"]:
        assert c["level"] is None or c["level"] == "none"


def test_univariate_route_empty_strategy_returns_empty_report(
    client: TestClient,
    db: Session,
    fetch_recorder: list[FetchCall],
) -> None:
    """Univariate report with 0 signals must return a valid empty response."""
    res = client.get(
        "/api/analytics/univariate/session_label?strategy=fvg-impulse",
    )
    assert res.status_code == 200
    body = res.json()
    assert body["param_name"] == "session_label"
    assert body["total_signals"] == 0
    assert body["buckets"] == []
