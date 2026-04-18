"""
tests/test_stats_routes.py
---------------------------
Integration tests for GET /api/trades/stats/equity-curve
and GET /api/trades/stats/daily-summary.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import make_trade

EQUITY_CURVE_URL = "/api/trades/stats/equity-curve"
DAILY_SUMMARY_URL = "/api/trades/stats/daily-summary"

BASE = datetime(2025, 5, 1, 10, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# equity-curve
# ---------------------------------------------------------------------------


def test_equity_curve_empty_returns_empty_list(client: TestClient) -> None:
    """No trades in DB → empty list with 200 status."""
    resp = client.get(EQUITY_CURVE_URL)
    assert resp.status_code == 200
    assert resp.json() == []


def test_equity_curve_returns_correct_shape(
    client: TestClient,
    db: Session,
) -> None:
    """Closed trades produce correctly shaped EquityCurvePoint items."""
    make_trade(
        db, status="closed", outcome="win",
        pnl_usd=100.0, pnl_pips=20.0,
        close_time=BASE,
    )
    resp = client.get(EQUITY_CURVE_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    point = data[0]
    assert "date" in point
    assert "close_time" in point
    assert "pnl_usd" in point
    assert "pnl_pips" in point
    assert "cumulative_pnl_usd" in point
    assert "cumulative_pnl_pips" in point
    assert "trade_count" in point
    assert "outcome" in point


def test_equity_curve_cumulative_values(
    client: TestClient,
    db: Session,
) -> None:
    """Cumulative P&L accumulates across multiple closed trades."""
    from datetime import timedelta

    make_trade(
        db, status="closed", outcome="win",
        pnl_usd=100.0, pnl_pips=20.0,
        close_time=BASE,
    )
    make_trade(
        db, status="closed", outcome="loss",
        pnl_usd=-40.0, pnl_pips=-8.0,
        close_time=BASE + timedelta(hours=1),
    )
    resp = client.get(EQUITY_CURVE_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["cumulative_pnl_usd"] == 100.0
    assert data[1]["cumulative_pnl_usd"] == 60.0


def test_equity_curve_open_trades_excluded(
    client: TestClient,
    db: Session,
) -> None:
    """Open trades do not appear in the equity curve."""
    make_trade(db, status="open")
    make_trade(
        db, status="closed", outcome="win",
        pnl_usd=50.0, pnl_pips=10.0,
        close_time=BASE,
    )
    resp = client.get(EQUITY_CURVE_URL)
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_equity_curve_requires_auth(raw_client: TestClient) -> None:
    """Request without Bearer token returns 401."""
    resp = raw_client.get(EQUITY_CURVE_URL)
    assert resp.status_code == 401


def test_equity_curve_strategy_filter(
    client: TestClient,
    db: Session,
) -> None:
    """strategy query param filters results to the matching strategy."""
    make_trade(
        db, strategy="fvg-impulse", status="closed", outcome="win",
        pnl_usd=100.0, pnl_pips=20.0,
        close_time=BASE,
    )
    make_trade(
        db, strategy="other-strat", status="closed", outcome="win",
        pnl_usd=200.0, pnl_pips=40.0,
        close_time=BASE,
    )
    resp = client.get(EQUITY_CURVE_URL, params={"strategy": "fvg-impulse"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["pnl_usd"] == 100.0


def test_equity_curve_symbol_filter(
    client: TestClient,
    db: Session,
) -> None:
    """symbol query param filters results to the matching symbol."""
    make_trade(
        db, symbol="EURUSD", status="closed", outcome="win",
        pnl_usd=80.0, pnl_pips=16.0,
        close_time=BASE,
    )
    make_trade(
        db, symbol="GBPUSD", status="closed", outcome="loss",
        pnl_usd=-30.0, pnl_pips=-6.0,
        close_time=BASE,
    )
    resp = client.get(EQUITY_CURVE_URL, params={"symbol": "EURUSD"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["pnl_usd"] == 80.0


# ---------------------------------------------------------------------------
# daily-summary
# ---------------------------------------------------------------------------


def test_daily_summary_empty_returns_empty_list(client: TestClient) -> None:
    """No trades in DB → empty list with 200 status."""
    resp = client.get(DAILY_SUMMARY_URL)
    assert resp.status_code == 200
    assert resp.json() == []


def test_daily_summary_returns_correct_shape(
    client: TestClient,
    db: Session,
) -> None:
    """Closed trades produce correctly shaped DailySummaryPoint items."""
    make_trade(
        db, status="closed", outcome="win",
        pnl_usd=60.0, pnl_pips=12.0,
        close_time=BASE,
    )
    resp = client.get(DAILY_SUMMARY_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    point = data[0]
    assert "date" in point
    assert "trades" in point
    assert "wins" in point
    assert "losses" in point
    assert "breakevens" in point
    assert "pnl_usd" in point
    assert "pnl_pips" in point


def test_daily_summary_aggregates_same_day(
    client: TestClient,
    db: Session,
) -> None:
    """Two trades on the same calendar day produce one bucket."""
    from datetime import timedelta

    make_trade(
        db, status="closed", outcome="win",
        pnl_usd=100.0, pnl_pips=20.0,
        close_time=BASE,
    )
    make_trade(
        db, status="closed", outcome="loss",
        pnl_usd=-50.0, pnl_pips=-10.0,
        close_time=BASE + timedelta(hours=2),
    )
    resp = client.get(DAILY_SUMMARY_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["trades"] == 2
    assert data[0]["wins"] == 1
    assert data[0]["losses"] == 1
    assert data[0]["pnl_usd"] == 50.0


def test_daily_summary_requires_auth(raw_client: TestClient) -> None:
    """Request without Bearer token returns 401."""
    resp = raw_client.get(DAILY_SUMMARY_URL)
    assert resp.status_code == 401


def test_daily_summary_strategy_filter(
    client: TestClient,
    db: Session,
) -> None:
    """strategy query param filters to the matching strategy only."""
    make_trade(
        db, strategy="fvg-impulse", status="closed", outcome="win",
        pnl_usd=100.0, pnl_pips=20.0,
        close_time=BASE,
    )
    make_trade(
        db, strategy="other-strat", status="closed", outcome="win",
        pnl_usd=200.0, pnl_pips=40.0,
        close_time=BASE,
    )
    resp = client.get(DAILY_SUMMARY_URL, params={"strategy": "fvg-impulse"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["pnl_usd"] == 100.0


def test_daily_summary_symbol_filter(
    client: TestClient,
    db: Session,
) -> None:
    """symbol query param filters to the matching symbol only."""
    make_trade(
        db, symbol="EURUSD", status="closed", outcome="win",
        pnl_usd=80.0, pnl_pips=16.0,
        close_time=BASE,
    )
    make_trade(
        db, symbol="GBPUSD", status="closed", outcome="loss",
        pnl_usd=-30.0, pnl_pips=-6.0,
        close_time=BASE,
    )
    resp = client.get(DAILY_SUMMARY_URL, params={"symbol": "GBPUSD"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["losses"] == 1
