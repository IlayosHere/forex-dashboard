"""
tests/test_economic_calendar.py
----------------------------------
Tests for shared/economic_calendar.py and the news/holiday stats wiring in
api/services/trade_stats_news.py.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.models import AccountModel
from shared.economic_calendar import coverage_through, economic_events_for_range
from shared.market_holidays import cme_coverage_through
from tests.conftest import TEST_USER, make_trade

# ---------------------------------------------------------------------------
# shared/economic_calendar.py — pure functions
# ---------------------------------------------------------------------------


def test_nfp_is_always_first_friday() -> None:
    """NFP for March 2026 is the first Friday: March 6, 2026."""
    results = economic_events_for_range(date(2026, 3, 1), date(2026, 3, 10))
    nfp = [r for r in results if r["name"] == "Non-Farm Payrolls"]
    assert len(nfp) == 1
    assert nfp[0]["date"] == "2026-03-06"
    assert nfp[0]["impact"] == "high"


def test_nfp_first_friday_across_years() -> None:
    """First-Friday rule holds for both 2025 and 2026."""
    results_2025 = economic_events_for_range(date(2025, 1, 1), date(2025, 1, 10))
    results_2026 = economic_events_for_range(date(2026, 1, 1), date(2026, 1, 10))
    nfp_2025 = next(r for r in results_2025 if r["name"] == "Non-Farm Payrolls")
    nfp_2026 = next(r for r in results_2026 if r["name"] == "Non-Farm Payrolls")
    assert date.fromisoformat(nfp_2025["date"]).weekday() == 4
    assert date.fromisoformat(nfp_2026["date"]).weekday() == 4


def test_fomc_known_2026_date() -> None:
    """The June 2026 FOMC decision lands on June 17, 2026."""
    results = economic_events_for_range(date(2026, 6, 15), date(2026, 6, 19))
    fomc = [r for r in results if r["name"] == "FOMC Rate Decision"]
    assert any(r["date"] == "2026-06-17" for r in fomc)


def test_cpi_known_2026_date() -> None:
    """January 2026 CPI was released January 13, 2026."""
    results = economic_events_for_range(date(2026, 1, 10), date(2026, 1, 15))
    cpi = [r for r in results if r["name"] == "CPI"]
    assert any(r["date"] == "2026-01-13" for r in cpi)


def test_events_excludes_dates_outside_range() -> None:
    """No events between two FOMC meetings with no overlap."""
    results = economic_events_for_range(date(2026, 2, 1), date(2026, 2, 5))
    assert results == []


def test_all_entries_are_high_or_medium_usd() -> None:
    """No low-impact entries exist in the table at all."""
    results = economic_events_for_range(date(2026, 1, 1), date(2026, 12, 31))
    assert all(r["impact"] in {"high", "medium"} for r in results)
    assert all(r["currency"] == "USD" for r in results)


def test_results_sorted_by_date() -> None:
    results = economic_events_for_range(date(2026, 1, 1), date(2026, 3, 31))
    dates = [r["date"] for r in results]
    assert dates == sorted(dates)


def test_news_coverage_through_is_the_most_limiting_table() -> None:
    """GDP's last confirmed entry (2026-05-28) is earlier than FOMC/CPI/PPI's,
    so it bounds the overall coverage — a single combined date can't overstate
    confidence in the least-covered table."""
    assert coverage_through() == date(2026, 5, 28)


def test_holiday_coverage_through_matches_cme_table_max() -> None:
    assert cme_coverage_through() == date(2026, 12, 31)


# ---------------------------------------------------------------------------
# api/services/trade_stats_news.py
# ---------------------------------------------------------------------------


@dataclass
class _Trade:
    """Minimal stand-in for TradeModel."""

    outcome: str | None = None
    rr_achieved: float | None = None
    pnl_usd: float | None = None
    pnl_pips: float | None = None
    open_time: datetime = field(
        default_factory=lambda: datetime(2026, 1, 13, 14, 0, tzinfo=timezone.utc),
    )


def test_aggregate_by_news_day_buckets_high_impact_day() -> None:
    from api.services.trade_stats_news import aggregate_by_news_day

    trades = [
        _Trade(outcome="win", rr_achieved=1.0, open_time=datetime(2026, 1, 13, 14, 0, tzinfo=timezone.utc)),
        _Trade(outcome="loss", rr_achieved=-1.0, open_time=datetime(2026, 1, 14, 14, 0, tzinfo=timezone.utc)),
    ]
    news_days = {date(2026, 1, 13): "high"}
    result = aggregate_by_news_day(trades, news_days)
    assert result["high"]["total"] == 1
    assert result["normal"]["total"] == 1


def test_aggregate_by_market_holiday_buckets_closure_day() -> None:
    from api.services.trade_stats_news import aggregate_by_market_holiday

    trades = [
        _Trade(outcome="win", rr_achieved=1.0, open_time=datetime(2026, 12, 25, 14, 0, tzinfo=timezone.utc)),
        _Trade(outcome="loss", rr_achieved=-1.0, open_time=datetime(2026, 1, 5, 14, 0, tzinfo=timezone.utc)),
    ]
    holiday_days = {date(2026, 12, 25): "full_close"}
    result = aggregate_by_market_holiday(trades, holiday_days)
    assert result["full_close"]["total"] == 1
    assert result["normal"]["total"] == 1


def test_build_news_day_map_collapses_to_high_when_both_present() -> None:
    from api.services.trade_stats_news import build_news_day_map

    # CPI release dates are "high" impact in our table; verify the map only
    # ever stores one bucket per date and never demotes a high day.
    result = build_news_day_map(date(2026, 1, 1), date(2026, 1, 31))
    assert result[date(2026, 1, 13)] == "high"


def test_build_holiday_day_map_includes_cme_and_thin_volume() -> None:
    from api.services.trade_stats_news import build_holiday_day_map

    result = build_holiday_day_map(date(2026, 12, 20), date(2026, 12, 26))
    assert result[date(2026, 12, 25)] == "full_close"


# ---------------------------------------------------------------------------
# GET /api/trades/stats?account_type=backtest — by_news_day / by_market_holiday
# ---------------------------------------------------------------------------


def _make_backtest_account(db: Session) -> AccountModel:
    acct = AccountModel(
        id=str(uuid.uuid4()),
        name="backtest account",
        account_type="backtest",
        instrument_type="futures_mnq",
        status="active",
        owner=TEST_USER,
        created_at=datetime.now(timezone.utc),
    )
    db.add(acct)
    db.commit()
    db.refresh(acct)
    return acct


def test_stats_includes_news_and_holiday_breakdowns_for_backtest(
    client: TestClient, db: Session,
) -> None:
    bt_acct = _make_backtest_account(db)
    make_trade(
        db, account_id=bt_acct.id, status="closed", outcome="win",
        pnl_pips=30.0, pnl_usd=60.0, rr_achieved=3.0,
        instrument_type="futures_mnq",
        open_time=datetime(2026, 1, 13, 14, 0, tzinfo=timezone.utc),  # CPI day
    )
    make_trade(
        db, account_id=bt_acct.id, status="closed", outcome="loss",
        pnl_pips=-20.0, pnl_usd=-40.0, rr_achieved=-2.0,
        instrument_type="futures_mnq",
        open_time=datetime(2026, 1, 20, 14, 0, tzinfo=timezone.utc),  # normal day
    )

    resp = client.get("/api/trades/stats", params={"account_type": "backtest"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_news_day"]["high"]["total"] == 1
    assert data["by_news_day"]["normal"]["total"] == 1
    assert data["by_market_holiday"]["normal"]["total"] == 2


def test_stats_includes_news_breakdown_for_live_accounts_too(
    client: TestClient, db: Session,
) -> None:
    """News/holiday breakdowns are computed for every account type, not just
    backtest — live trading is exactly where the trader most cares whether
    news days actually hurt their real money."""
    live_acct = AccountModel(
        id=str(uuid.uuid4()), name="live", account_type="live",
        instrument_type="futures_mnq", status="active", owner=TEST_USER,
        created_at=datetime.now(timezone.utc),
    )
    db.add(live_acct)
    db.commit()
    make_trade(
        db, account_id=live_acct.id, status="closed", outcome="win",
        pnl_pips=10.0, pnl_usd=20.0, rr_achieved=1.0,
        instrument_type="futures_mnq",
        open_time=datetime(2026, 6, 17, 14, 0, tzinfo=timezone.utc),  # FOMC day
    )

    resp = client.get("/api/trades/stats", params={"account_type": "live"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["by_news_day"]["high"]["total"] == 1
    assert data["news_data_coverage_through"] == "2026-05-28"
    assert data["holiday_data_coverage_through"] == "2026-12-31"


# ---------------------------------------------------------------------------
# GET /api/trades/day-types
# ---------------------------------------------------------------------------


def test_day_types_returns_news_and_holiday_flags(client: TestClient) -> None:
    resp = client.get(
        "/api/trades/day-types",
        params={"from": "2026-01-10", "to": "2026-01-15"},
    )
    assert resp.status_code == 200
    data = resp.json()
    by_date = {d["date"]: d for d in data}
    assert by_date["2026-01-13"]["news_impact"] == "high"
    assert by_date["2026-01-13"]["market_status"] is None


def test_day_types_includes_holiday_entry(client: TestClient) -> None:
    resp = client.get(
        "/api/trades/day-types",
        params={"from": "2026-12-23", "to": "2026-12-26"},
    )
    assert resp.status_code == 200
    by_date = {d["date"]: d for d in resp.json()}
    assert by_date["2026-12-25"]["market_status"] == "full_close"
    assert by_date["2026-12-25"]["holiday_events"][0]["label"] == "CME Globex — Christmas Day"


def test_day_types_includes_full_news_event_entries(client: TestClient) -> None:
    resp = client.get(
        "/api/trades/day-types",
        params={"from": "2026-01-10", "to": "2026-01-15"},
    )
    assert resp.status_code == 200
    by_date = {d["date"]: d for d in resp.json()}
    assert by_date["2026-01-13"]["news_events"][0]["name"] == "CPI"


def test_day_types_requires_auth(raw_client: TestClient) -> None:
    resp = raw_client.get(
        "/api/trades/day-types",
        params={"from": "2026-01-01", "to": "2026-01-31"},
    )
    assert resp.status_code == 401
