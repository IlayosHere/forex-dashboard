"""
tests/test_trade_stats_extended.py
-----------------------------------
Unit tests for api/services/trade_stats_extended.py pure functions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from api.services.trade_stats_extended import (
    aggregate_by_assessment,
    aggregate_by_criteria_met,
    aggregate_by_day_of_week,
    aggregate_by_rule_compliance,
    aggregate_by_session,
    build_daily_summary,
    build_equity_curve,
    calculate_edge_metrics,
)
from tests.conftest import make_trade

BASE = datetime(2025, 3, 3, 10, 0, tzinfo=timezone.utc)  # Monday


# ---------------------------------------------------------------------------
# build_equity_curve
# ---------------------------------------------------------------------------


def test_equity_curve_accumulates_pnl(db: Session) -> None:
    """Cumulative USD and pip totals grow correctly across three trades."""
    t1 = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=100.0, pnl_pips=20.0,
        close_time=BASE,
    )
    t2 = make_trade(
        db, status="closed", outcome="loss",
        pnl_usd=-50.0, pnl_pips=-10.0,
        close_time=BASE + timedelta(hours=1),
    )
    t3 = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=75.0, pnl_pips=15.0,
        close_time=BASE + timedelta(hours=2),
    )
    result = build_equity_curve([t1, t2, t3])
    assert len(result) == 3
    assert result[0]["cumulative_pnl_usd"] == 100.0
    assert result[1]["cumulative_pnl_usd"] == 50.0
    assert result[2]["cumulative_pnl_usd"] == 125.0
    assert result[2]["cumulative_pnl_pips"] == 25.0


def test_equity_curve_sorted_by_close_time(db: Session) -> None:
    """Trades inserted out of order are sorted by open_time."""
    t_late = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=200.0, pnl_pips=40.0,
        open_time=BASE + timedelta(hours=5),
    )
    t_early = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=50.0, pnl_pips=10.0,
        open_time=BASE,
    )
    result = build_equity_curve([t_late, t_early])
    assert result[0]["pnl_usd"] == 50.0
    assert result[1]["pnl_usd"] == 200.0
    assert result[1]["cumulative_pnl_usd"] == 250.0


def test_equity_curve_date_field_is_iso_date(db: Session) -> None:
    """Each point's date field is an ISO date string."""
    t = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=10.0, pnl_pips=5.0,
        open_time=datetime(2025, 6, 15, 9, 0, tzinfo=timezone.utc),
    )
    result = build_equity_curve([t])
    assert result[0]["date"] == "2025-06-15"


def test_equity_curve_empty_returns_empty() -> None:
    """Empty trade list produces empty curve."""
    assert build_equity_curve([]) == []


def test_equity_curve_none_pnl_treated_as_zero(db: Session) -> None:
    """Trades with None pnl_usd/pnl_pips contribute zero to cumulative totals."""
    t = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=None, pnl_pips=None,
        close_time=BASE,
    )
    result = build_equity_curve([t])
    assert result[0]["pnl_usd"] == 0.0
    assert result[0]["cumulative_pnl_usd"] == 0.0


# ---------------------------------------------------------------------------
# build_daily_summary
# ---------------------------------------------------------------------------


def test_daily_summary_aggregates_by_day(db: Session) -> None:
    """Two trades on the same day appear as one bucket."""
    day = datetime(2025, 4, 1, tzinfo=timezone.utc)
    t1 = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=80.0, pnl_pips=16.0,
        open_time=day,
    )
    t2 = make_trade(
        db, status="closed", outcome="loss",
        pnl_usd=-40.0, pnl_pips=-8.0,
        open_time=day + timedelta(hours=3),
    )
    result = build_daily_summary([t1, t2])
    assert len(result) == 1
    bucket = result[0]
    assert bucket["date"] == "2025-04-01"
    assert bucket["trades"] == 2
    assert bucket["wins"] == 1
    assert bucket["losses"] == 1
    assert bucket["pnl_usd"] == 40.0
    assert bucket["pnl_pips"] == 8.0


def test_daily_summary_separate_days(db: Session) -> None:
    """Trades on different days produce separate buckets in date order."""
    t1 = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=50.0, pnl_pips=10.0,
        open_time=datetime(2025, 4, 2, tzinfo=timezone.utc),
    )
    t2 = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=30.0, pnl_pips=6.0,
        open_time=datetime(2025, 4, 1, tzinfo=timezone.utc),
    )
    result = build_daily_summary([t1, t2])
    assert len(result) == 2
    assert result[0]["date"] == "2025-04-01"
    assert result[1]["date"] == "2025-04-02"


def test_daily_summary_breakeven_counted(db: Session) -> None:
    """Breakeven trades are counted in the breakevens field."""
    t = make_trade(
        db, status="closed", outcome="breakeven",
        pnl_usd=0.0, pnl_pips=0.0,
        close_time=BASE,
    )
    result = build_daily_summary([t])
    assert result[0]["breakevens"] == 1
    assert result[0]["wins"] == 0
    assert result[0]["losses"] == 0


def test_daily_summary_empty_returns_empty() -> None:
    """Empty trade list produces empty list."""
    assert build_daily_summary([]) == []


# ---------------------------------------------------------------------------
# calculate_edge_metrics
# ---------------------------------------------------------------------------


def test_edge_metrics_win_loss_averages(db: Session) -> None:
    """avg_win and avg_loss are calculated correctly from pips and usd."""
    t_win = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=20.0, pnl_usd=100.0,
    )
    t_loss = make_trade(
        db, status="closed", outcome="loss",
        pnl_pips=-10.0, pnl_usd=-50.0,
    )
    m = calculate_edge_metrics([t_win, t_loss])
    assert m["avg_win_pips"] == 20.0
    assert m["avg_loss_pips"] == 10.0
    assert m["avg_win_usd"] == 100.0
    assert m["avg_loss_usd"] == 50.0


def test_edge_metrics_expectancy(db: Session) -> None:
    """Expectancy = win_rate * avg_win - loss_rate * avg_loss."""
    t_win = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=20.0, pnl_usd=100.0,
    )
    t_loss = make_trade(
        db, status="closed", outcome="loss",
        pnl_pips=-10.0, pnl_usd=-50.0,
    )
    m = calculate_edge_metrics([t_win, t_loss])
    # win_rate = 0.5, loss_rate = 0.5
    # expectancy_usd = 0.5 * 100 - 0.5 * 50 = 25.0
    assert m["expectancy_usd"] == 25.0
    assert m["expectancy_pips"] == 5.0


def test_edge_metrics_all_wins_no_expectancy(db: Session) -> None:
    """Without any losses, expectancy is None (cannot compute loss rate)."""
    t = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=20.0, pnl_usd=100.0,
    )
    m = calculate_edge_metrics([t])
    assert m["expectancy_usd"] is None
    assert m["avg_loss_pips"] is None


def test_edge_metrics_empty_returns_nones() -> None:
    """Empty list returns all None metrics."""
    m = calculate_edge_metrics([])
    assert m["avg_win_pips"] is None
    assert m["avg_loss_pips"] is None
    assert m["expectancy_usd"] is None
    assert m["consistency_ratio"] is None


def test_edge_metrics_consistency_ratio(db: Session) -> None:
    """Weeks with net positive R count toward consistency_ratio."""
    week1_monday = datetime(2025, 3, 3, 10, 0, tzinfo=timezone.utc)
    week2_monday = datetime(2025, 3, 10, 10, 0, tzinfo=timezone.utc)
    t1 = make_trade(
        db, status="closed", outcome="win",
        pnl_usd=100.0, rr_achieved=2.0,
        open_time=week1_monday,
    )
    t2 = make_trade(
        db, status="closed", outcome="loss",
        pnl_usd=-200.0, rr_achieved=-1.0,
        open_time=week2_monday,
    )
    m = calculate_edge_metrics([t1, t2])
    # Week 1: +2.0R (positive), Week 2: -1.0R (negative) → 50% consistency
    assert m["consistency_ratio"] == 50.0


# ---------------------------------------------------------------------------
# aggregate_by_session
# ---------------------------------------------------------------------------


def test_aggregate_by_session_buckets(db: Session) -> None:
    """Trades with different open_time hours land in the correct session buckets."""
    asian_time = BASE.replace(hour=3)   # 03:00 UTC → asian
    london_time = BASE.replace(hour=9)  # 09:00 UTC → london
    t_asian = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=10.0, pnl_usd=50.0,
        open_time=asian_time,
    )
    t_london = make_trade(
        db, status="closed", outcome="loss",
        pnl_pips=-5.0, pnl_usd=-25.0,
        open_time=london_time,
    )
    result = aggregate_by_session([t_asian, t_london])
    assert "asian" in result
    assert "london" in result
    assert result["asian"]["total"] == 1
    assert result["london"]["total"] == 1


def test_aggregate_by_session_win_rate(db: Session) -> None:
    """Win rate per session is calculated correctly."""
    london_win = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=20.0, pnl_usd=100.0,
        open_time=BASE.replace(hour=9),
    )
    london_loss = make_trade(
        db, status="closed", outcome="loss",
        pnl_pips=-10.0, pnl_usd=-50.0,
        open_time=BASE.replace(hour=11),
    )
    result = aggregate_by_session([london_win, london_loss])
    assert result["london"]["wins"] == 1
    assert result["london"]["losses"] == 1
    assert result["london"]["win_rate"] == 50.0


def test_aggregate_by_session_name_field(db: Session) -> None:
    """Each session bucket has a 'name' field matching its key."""
    t = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=10.0, pnl_usd=50.0,
        open_time=BASE.replace(hour=14),  # 14:00 → overlap
    )
    result = aggregate_by_session([t])
    assert "overlap" in result
    assert result["overlap"]["name"] == "overlap"


# ---------------------------------------------------------------------------
# aggregate_by_day_of_week
# ---------------------------------------------------------------------------


def test_aggregate_by_day_of_week_keys(db: Session) -> None:
    """Weekday index keys are present and have human-readable name fields."""
    monday_trade = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=10.0, pnl_usd=50.0,
        open_time=datetime(2025, 3, 3, 10, tzinfo=timezone.utc),  # Monday
    )
    result = aggregate_by_day_of_week([monday_trade])
    assert "0" in result  # Monday weekday() == 0
    assert result["0"]["name"] == "Monday"
    assert result["0"]["total"] == 1


def test_aggregate_by_day_of_week_multiple_days(db: Session) -> None:
    """Trades on different days produce separate weekday buckets."""
    monday = datetime(2025, 3, 3, 10, tzinfo=timezone.utc)
    wednesday = datetime(2025, 3, 5, 10, tzinfo=timezone.utc)
    t_mon = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=10.0, pnl_usd=50.0,
        open_time=monday,
    )
    t_wed = make_trade(
        db, status="closed", outcome="loss",
        pnl_pips=-5.0, pnl_usd=-25.0,
        open_time=wednesday,
    )
    result = aggregate_by_day_of_week([t_mon, t_wed])
    assert "0" in result  # Monday
    assert "2" in result  # Wednesday
    assert result["0"]["wins"] == 1
    assert result["2"]["losses"] == 1


# ---------------------------------------------------------------------------
# aggregate_by_confidence / aggregate_by_rating
# ---------------------------------------------------------------------------


def test_aggregate_by_confidence_buckets(db: Session) -> None:
    """Trades with confidence set are grouped by their integer value."""
    t_high = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=20.0, pnl_usd=100.0,
    )
    t_high.confidence = 5
    t_low = make_trade(
        db, status="closed", outcome="loss",
        pnl_pips=-10.0, pnl_usd=-50.0,
    )
    t_low.confidence = 2
    result = aggregate_by_assessment([t_high, t_low], "confidence")
    assert "5" in result
    assert "2" in result
    assert result["5"]["wins"] == 1
    assert result["2"]["losses"] == 1


def test_aggregate_by_rating_buckets(db: Session) -> None:
    """Trades with rating set are grouped by their integer value."""
    t = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=15.0, pnl_usd=75.0,
    )
    t.rating = 4
    result = aggregate_by_assessment([t], "rating")
    assert "4" in result
    assert result["4"]["total"] == 1
    assert result["4"]["name"] == "4"


def test_aggregate_by_confidence_none_excluded(db: Session) -> None:
    """Trades with None confidence are excluded from results."""
    t = make_trade(
        db, status="closed", outcome="win",
        pnl_pips=10.0, pnl_usd=50.0,
    )
    # confidence defaults to None in make_trade
    result = aggregate_by_assessment([t], "confidence")
    assert result == {}


# ---------------------------------------------------------------------------
# aggregate_by_criteria_met
# ---------------------------------------------------------------------------


def test_criteria_met_excludes_none(db: Session) -> None:
    """Trades with criteria_met_at_entry=None are not included in any bucket."""
    make_trade(db, status="closed", outcome="win", pnl_usd=100.0, pnl_pips=10.0,
               criteria_met_at_entry=None)
    t2 = make_trade(db, status="closed", outcome="win", pnl_usd=100.0, pnl_pips=10.0,
                    criteria_met_at_entry=None)
    result = aggregate_by_criteria_met([t2])
    assert result == {}


def test_criteria_met_buckets_correct(db: Session) -> None:
    """True maps to 'met', False maps to 'not_met'."""
    t_met = make_trade(db, status="closed", outcome="win", pnl_usd=80.0, pnl_pips=8.0,
                       criteria_met_at_entry=True)
    t_not = make_trade(db, status="closed", outcome="loss", pnl_usd=-40.0, pnl_pips=-4.0,
                       criteria_met_at_entry=False)
    result = aggregate_by_criteria_met([t_met, t_not])
    assert "met" in result
    assert "not_met" in result
    assert result["met"]["total"] == 1
    assert result["not_met"]["total"] == 1


def test_criteria_met_win_rate(db: Session) -> None:
    """Win rate is computed correctly per bucket."""
    t1 = make_trade(db, status="closed", outcome="win", pnl_usd=100.0, pnl_pips=10.0,
                    criteria_met_at_entry=True)
    t2 = make_trade(db, status="closed", outcome="win", pnl_usd=80.0, pnl_pips=8.0,
                    criteria_met_at_entry=True)
    t3 = make_trade(db, status="closed", outcome="loss", pnl_usd=-50.0, pnl_pips=-5.0,
                    criteria_met_at_entry=False)
    result = aggregate_by_criteria_met([t1, t2, t3])
    assert result["met"]["win_rate"] == 100.0
    assert result["not_met"]["win_rate"] == 0.0  # 0 wins / 1 loss → 0.0%


def test_criteria_met_avg_rr_populated(db: Session) -> None:
    """avg_rr is populated from rr_achieved values."""
    t = make_trade(db, status="closed", outcome="win", pnl_usd=100.0, pnl_pips=10.0,
                   rr_achieved=2.5, criteria_met_at_entry=True)
    result = aggregate_by_criteria_met([t])
    assert result["met"]["avg_rr"] == 2.5


def test_criteria_met_avg_rr_none_when_no_rr(db: Session) -> None:
    """avg_rr is None when no rr_achieved values in the bucket."""
    t = make_trade(db, status="closed", outcome="win", pnl_usd=100.0, pnl_pips=10.0,
                   rr_achieved=None, criteria_met_at_entry=True)
    result = aggregate_by_criteria_met([t])
    assert result["met"]["avg_rr"] is None


def test_criteria_met_mixed_none_excluded(db: Session) -> None:
    """None trades are excluded even when mixed with non-None trades."""
    t_met = make_trade(db, status="closed", outcome="win", pnl_usd=100.0, pnl_pips=10.0,
                       criteria_met_at_entry=True)
    t_not = make_trade(db, status="closed", outcome="loss", pnl_usd=-40.0, pnl_pips=-4.0,
                       criteria_met_at_entry=False)
    t_none = make_trade(db, status="closed", outcome="win", pnl_usd=60.0, pnl_pips=6.0,
                        criteria_met_at_entry=None)
    result = aggregate_by_criteria_met([t_met, t_not, t_none])
    total_counted = result["met"]["total"] + result["not_met"]["total"]
    assert total_counted == 2


def test_criteria_met_name_field(db: Session) -> None:
    """Each bucket has a 'name' field matching the key."""
    t = make_trade(db, status="closed", outcome="win", pnl_usd=100.0, pnl_pips=10.0,
                   criteria_met_at_entry=True)
    result = aggregate_by_criteria_met([t])
    assert result["met"]["name"] == "met"


# ---------------------------------------------------------------------------
# aggregate_by_rule_compliance
# ---------------------------------------------------------------------------


def test_rule_compliance_three_way_split(db: Session) -> None:
    """True→compliant, False→mistake, None→unreviewed; all three buckets present."""
    t_ok = make_trade(db, status="closed", outcome="win", pnl_usd=100.0, pnl_pips=10.0,
                      rule_followed=True)
    t_err = make_trade(db, status="closed", outcome="loss", pnl_usd=-50.0, pnl_pips=-5.0,
                       rule_followed=False)
    t_none = make_trade(db, status="closed", outcome="win", pnl_usd=80.0, pnl_pips=8.0,
                        rule_followed=None)
    result = aggregate_by_rule_compliance([t_ok, t_err, t_none])
    assert "compliant" in result
    assert "mistake" in result
    assert "unreviewed" in result
    assert result["compliant"]["total"] == 1
    assert result["mistake"]["total"] == 1
    assert result["unreviewed"]["total"] == 1


def test_rule_compliance_win_rate(db: Session) -> None:
    """Win rate is computed per bucket from decisive trades only."""
    t1 = make_trade(db, status="closed", outcome="win", pnl_usd=80.0, pnl_pips=8.0,
                    rule_followed=True)
    t2 = make_trade(db, status="closed", outcome="loss", pnl_usd=-40.0, pnl_pips=-4.0,
                    rule_followed=True)
    result = aggregate_by_rule_compliance([t1, t2])
    assert result["compliant"]["win_rate"] == 50.0


def test_rule_compliance_avg_rr(db: Session) -> None:
    """avg_rr is populated per bucket from rr_achieved."""
    t_ok = make_trade(db, status="closed", outcome="win", pnl_usd=90.0, pnl_pips=9.0,
                      rr_achieved=1.8, rule_followed=True)
    t_err = make_trade(db, status="closed", outcome="loss", pnl_usd=-45.0, pnl_pips=-4.5,
                       rr_achieved=0.5, rule_followed=False)
    result = aggregate_by_rule_compliance([t_ok, t_err])
    assert result["compliant"]["avg_rr"] == 1.8
    assert result["mistake"]["avg_rr"] == 0.5


def test_rule_compliance_unreviewed_pnl(db: Session) -> None:
    """Unreviewed bucket accumulates pnl_usd correctly."""
    t = make_trade(db, status="closed", outcome="win", pnl_usd=75.0, pnl_pips=7.5,
                   rule_followed=None)
    result = aggregate_by_rule_compliance([t])
    assert result["unreviewed"]["total_pnl_usd"] == 75.0


def test_rule_compliance_name_fields(db: Session) -> None:
    """Each bucket has a 'name' field matching its key."""
    t = make_trade(db, status="closed", outcome="win", pnl_usd=100.0, pnl_pips=10.0,
                   rule_followed=True)
    result = aggregate_by_rule_compliance([t])
    assert result["compliant"]["name"] == "compliant"
