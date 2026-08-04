"""
tests/test_mistake_stats.py
----------------------------
Tests for per-mistake statistics:
- GET /api/trades/stats/mistakes (regression after refactor to aggregate_mistakes)
- GET /api/trades/stats/mistakes/timeseries (new weekly/monthly bucketing)
- api/services/trade_stats_mistakes.build_mistake_timeseries (pure function)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models import TradeMistakeModel, TradeModel
from api.services.trade_stats_mistakes import build_mistake_timeseries
from tests.conftest import TEST_USER, make_trade

MISTAKES_URL = "/api/trades/stats/mistakes"
TIMESERIES_URL = "/api/trades/stats/mistakes/timeseries"

# Monday, ISO week 2025-W10.
BASE = datetime(2025, 3, 3, 10, 0, tzinfo=timezone.utc)
# Monday, calendar year 2025 but ISO week 2026-W01 (year-boundary case).
YEAR_BOUNDARY = datetime(2025, 12, 29, 9, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _link(trade_id: str, mistake_id: str) -> TradeMistakeModel:
    """Build an in-memory (unpersisted) TradeMistakeModel link."""
    return TradeMistakeModel(
        trade_id=trade_id, mistake_id=mistake_id,
        linked_at=datetime.now(timezone.utc),
    )


def _bare_trade(*, open_time: datetime | None, pnl_usd: float, outcome: str) -> TradeModel:
    """Build an in-memory TradeModel, allowing open_time=None.

    The real `open_time` column is NOT NULL, but build_mistake_timeseries
    must defensively skip a None open_time the same way
    trade_stats_extended.build_daily_summary does — this can only be
    exercised with an unpersisted in-memory object.
    """
    now = datetime.now(timezone.utc)
    return TradeModel(
        id=str(uuid.uuid4()), owner=TEST_USER, strategy="s", symbol="MNQ",
        instrument_type="futures", direction="BUY", entry_price=100.0,
        sl_price=99.0, lot_size=1.0, status="closed", outcome=outcome,
        pnl_usd=pnl_usd, rr_achieved=None, risk_pips=10.0,
        open_time=open_time, tags=[], notes="", trade_metadata={},
        created_at=now, updated_at=now,
    )


def _link_mistake_via_api(client: TestClient, trade_id: str, name: str) -> None:
    resp = client.post(f"/api/trades/{trade_id}/mistakes", json={"name": name})
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# build_mistake_timeseries — pure function unit tests
# ---------------------------------------------------------------------------


def test_timeseries_week_bucketing() -> None:
    """Two trades in the same ISO week produce one bucket with correct bounds."""
    t1 = _bare_trade(open_time=BASE, pnl_usd=-50.0, outcome="loss")
    t2 = _bare_trade(open_time=BASE.replace(hour=14), pnl_usd=-30.0, outcome="loss")
    links = [_link(t1.id, "m1"), _link(t2.id, "m1")]

    result = build_mistake_timeseries([t1, t2], links, {"m1": "FOMO entry"}, "week")

    assert len(result) == 1
    bucket = result[0]
    assert bucket["period"] == "2025-W10"
    assert bucket["period_start"] == "2025-03-03"
    assert bucket["period_end"] == "2025-03-09"
    assert bucket["total_mistake_trades"] == 2
    assert bucket["total_pnl_usd"] == -80.0
    assert len(bucket["mistakes"]) == 1
    assert bucket["mistakes"][0]["name"] == "FOMO entry"
    assert bucket["mistakes"][0]["count"] == 2
    assert bucket["mistakes"][0]["total_pnl_usd"] == -80.0


def test_timeseries_month_bucketing() -> None:
    """A trade in July 2026 buckets into the correct month with month-end bounds."""
    t1 = _bare_trade(
        open_time=datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc),
        pnl_usd=40.0, outcome="win",
    )
    links = [_link(t1.id, "m1")]

    result = build_mistake_timeseries([t1], links, {"m1": "Oversized lot"}, "month")

    assert len(result) == 1
    bucket = result[0]
    assert bucket["period"] == "2026-07"
    assert bucket["period_start"] == "2026-07-01"
    assert bucket["period_end"] == "2026-07-31"
    assert bucket["total_mistake_trades"] == 1
    assert bucket["total_pnl_usd"] == 40.0


def test_timeseries_two_periods_chronological_order() -> None:
    """Periods are returned in ascending chronological order."""
    t_march = _bare_trade(open_time=BASE, pnl_usd=-10.0, outcome="loss")
    t_july = _bare_trade(
        open_time=datetime(2025, 7, 1, 9, 0, tzinfo=timezone.utc),
        pnl_usd=-20.0, outcome="loss",
    )
    links = [_link(t_march.id, "m1"), _link(t_july.id, "m1")]

    result = build_mistake_timeseries([t_march, t_july], links, {"m1": "x"}, "week")

    assert len(result) == 2
    assert result[0]["period"] < result[1]["period"]
    assert result[0]["period"] == "2025-W10"


def test_timeseries_iso_week_year_boundary() -> None:
    """Late-December trade that falls in ISO week 1 of the next year buckets there."""
    t1 = _bare_trade(open_time=YEAR_BOUNDARY, pnl_usd=-15.0, outcome="loss")
    links = [_link(t1.id, "m1")]

    result = build_mistake_timeseries([t1], links, {"m1": "Revenge trade"}, "week")

    assert len(result) == 1
    bucket = result[0]
    assert bucket["period"] == "2026-W01"
    assert bucket["period_start"] == "2025-12-29"
    assert bucket["period_end"] == "2026-01-04"


def test_timeseries_trade_with_two_mistakes_counts_once() -> None:
    """A trade linked to 2 mistakes counts once toward totals but appears in both rows."""
    t1 = _bare_trade(open_time=BASE, pnl_usd=-100.0, outcome="loss")
    links = [_link(t1.id, "m1"), _link(t1.id, "m2")]
    name_map = {"m1": "FOMO entry", "m2": "Moved stop loss"}

    result = build_mistake_timeseries([t1], links, name_map, "week")

    assert len(result) == 1
    bucket = result[0]
    assert bucket["total_mistake_trades"] == 1
    assert bucket["total_pnl_usd"] == -100.0
    assert len(bucket["mistakes"]) == 2
    names = {row["name"] for row in bucket["mistakes"]}
    assert names == {"FOMO entry", "Moved stop loss"}
    for row in bucket["mistakes"]:
        assert row["count"] == 1
        assert row["total_pnl_usd"] == -100.0


def test_timeseries_skips_trades_with_none_open_time() -> None:
    """A link whose trade has open_time=None is skipped, not an error."""
    t_valid = _bare_trade(open_time=BASE, pnl_usd=10.0, outcome="win")
    t_no_time = _bare_trade(open_time=None, pnl_usd=999.0, outcome="win")
    links = [_link(t_valid.id, "m1"), _link(t_no_time.id, "m1")]

    result = build_mistake_timeseries([t_valid, t_no_time], links, {"m1": "x"}, "week")

    assert len(result) == 1
    assert result[0]["total_mistake_trades"] == 1
    assert result[0]["total_pnl_usd"] == 10.0


def test_timeseries_empty_links_returns_empty_list() -> None:
    """No mistake links produces no periods."""
    t1 = _bare_trade(open_time=BASE, pnl_usd=10.0, outcome="win")
    assert build_mistake_timeseries([t1], [], {}, "week") == []


def test_timeseries_invalid_granularity_raises_value_error() -> None:
    """An unsupported granularity raises ValueError (route converts to 422)."""
    t1 = _bare_trade(open_time=BASE, pnl_usd=10.0, outcome="win")
    links = [_link(t1.id, "m1")]
    try:
        build_mistake_timeseries([t1], links, {"m1": "x"}, "quarter")
        raised = False
    except ValueError:
        raised = True
    assert raised


# ---------------------------------------------------------------------------
# GET /api/trades/stats/mistakes/timeseries — route tests
# ---------------------------------------------------------------------------


def test_timeseries_route_empty_returns_empty_list(client: TestClient) -> None:
    """No trades in DB -> empty list with 200 status."""
    resp = client.get(TIMESERIES_URL)
    assert resp.status_code == 200
    assert resp.json() == []


def test_timeseries_route_default_granularity_is_week(
    client: TestClient,
    db: Session,
) -> None:
    """Without a granularity param, trades bucket by ISO week."""
    trade = make_trade(
        db, status="closed", outcome="loss",
        pnl_usd=-25.0, open_time=BASE,
    )
    _link_mistake_via_api(client, trade.id, "Chased price")

    resp = client.get(TIMESERIES_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["period"] == "2025-W10"
    assert data[0]["mistakes"][0]["name"] == "Chased price"


def test_timeseries_route_month_granularity(
    client: TestClient,
    db: Session,
) -> None:
    """granularity=month buckets by calendar month."""
    trade = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=15.0, open_time=BASE,
    )
    _link_mistake_via_api(client, trade.id, "Ignored plan")

    resp = client.get(TIMESERIES_URL, params={"granularity": "month"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["period"] == "2025-03"


def test_timeseries_route_invalid_granularity_returns_422(client: TestClient) -> None:
    """An unsupported granularity value is rejected by FastAPI param validation."""
    resp = client.get(TIMESERIES_URL, params={"granularity": "quarter"})
    assert resp.status_code == 422


def test_timeseries_route_requires_auth(raw_client: TestClient) -> None:
    """Request without Bearer token returns 401."""
    resp = raw_client.get(TIMESERIES_URL)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /api/trades/stats/mistakes — regression after refactor
# ---------------------------------------------------------------------------


def test_flat_mistakes_route_empty_returns_empty_list(client: TestClient) -> None:
    """No trades in DB -> empty list with 200 status (unchanged behavior)."""
    resp = client.get(MISTAKES_URL)
    assert resp.status_code == 200
    assert resp.json() == []


def test_flat_mistakes_route_aggregates_and_sorts_worst_first(
    client: TestClient,
    db: Session,
) -> None:
    """Two mistakes aggregate independently and sort worst total_pnl_usd first."""
    losing_trade = make_trade(
        db, status="closed", outcome="loss",
        pnl_usd=-200.0, rr_achieved=-1.0, open_time=BASE,
    )
    winning_trade = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=50.0, rr_achieved=1.5, open_time=BASE,
    )
    _link_mistake_via_api(client, losing_trade.id, "Oversized lot")
    _link_mistake_via_api(client, winning_trade.id, "Late entry")

    resp = client.get(MISTAKES_URL)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    # Worst P&L first.
    assert data[0]["name"] == "Oversized lot"
    assert data[0]["total_pnl_usd"] == -200.0
    assert data[0]["wins"] == 0
    assert data[0]["losses"] == 1
    assert data[0]["win_rate"] == 0.0
    assert data[1]["name"] == "Late entry"
    assert data[1]["total_pnl_usd"] == 50.0
    assert data[1]["avg_rr"] == 1.5


def test_flat_mistakes_route_requires_auth(raw_client: TestClient) -> None:
    """Request without Bearer token returns 401 (unchanged behavior)."""
    resp = raw_client.get(MISTAKES_URL)
    assert resp.status_code == 401
