"""
tests/test_trade_stats_time.py
------------------------------
Unit tests for the time-of-day classifiers and api/services/trade_stats_time.py.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from api.models import TradeModel
from api.services.ict_classifiers import (
    classify_macro,
    classify_ny_phase,
    classify_time_slice,
)
from api.services.trade_stats_time import MIN_SAMPLE, compute_time_edge
from tests.conftest import make_trade

MONDAY = datetime(2025, 3, 3)  # Monday


def _at(hour: int, minute: int) -> datetime:
    return MONDAY.replace(hour=hour, minute=minute)


def _trade(
    db: Session, at: datetime, outcome: str, setup: str | None = None, tf: str | None = None,
) -> TradeModel:
    win = outcome == "win"
    trade = make_trade(
        db, status="closed", outcome=outcome, open_time=at,
        pnl_usd=100.0 if win else -50.0, rr_achieved=2.0 if win else -1.0,
    )
    trade.ict_setup_type = setup
    trade.ict_ifvg_timeframe = tf
    return trade


def test_ny_phase_boundaries() -> None:
    assert classify_ny_phase(_at(9, 29)) == "pre_open"
    assert classify_ny_phase(_at(9, 30)) == "judas"
    assert classify_ny_phase(_at(9, 44)) == "judas"
    assert classify_ny_phase(_at(9, 45)) == "post_judas"
    assert classify_ny_phase(_at(10, 0)) == "ny_open"
    assert classify_ny_phase(_at(10, 29)) == "ny_open"
    assert classify_ny_phase(_at(10, 30)) == "late_session"
    assert classify_ny_phase(_at(11, 0)) == "after_session"
    assert classify_ny_phase(_at(15, 59)) == "after_session"
    assert classify_ny_phase(_at(17, 0)) == "other"


def test_time_slice_is_fifteen_minute_bucket() -> None:
    assert classify_time_slice(_at(9, 30)) == "09:30"
    assert classify_time_slice(_at(9, 44)) == "09:30"
    assert classify_time_slice(_at(9, 45)) == "09:45"
    assert classify_time_slice(_at(10, 0)) == "10:00"
    assert classify_time_slice(_at(7, 0)) == "other"


def test_macro_window_spans_xx50_to_xx10() -> None:
    assert classify_macro(_at(9, 50)) == "09:50-10:10"
    assert classify_macro(_at(10, 9)) == "09:50-10:10"
    assert classify_macro(_at(10, 10)) == "outside"
    assert classify_macro(_at(10, 50)) == "10:50-11:10"


def test_phase_stats_and_empty_buckets(db: Session) -> None:
    trades = [
        _trade(db, _at(10, 5), "win"),
        _trade(db, _at(10, 20), "loss"),
        _trade(db, _at(14, 0), "win"),
    ]
    result = compute_time_edge(trades)
    sb = result["by_ny_phase"]["ny_open"]
    assert (sb["total"], sb["wins"], sb["losses"]) == (2, 1, 1)
    assert result["by_ny_phase"]["judas"]["total"] == 0
    assert result["by_time_slice"]["10:00"]["total"] == 1
    assert result["by_time_slice"]["10:15"]["total"] == 1
    assert result["by_macro"]["outside"]["total"] == 1
    assert result["by_macro"]["09:50-10:10"]["total"] == 1
    assert result["by_macro"]["13:50-14:10"]["total"] == 1


def test_setup_by_phase_matrix_separates_setups(db: Session) -> None:
    trades = [
        _trade(db, _at(10, 5), "win", setup="liquidity_sweep"),
        _trade(db, _at(10, 6), "loss", setup="continuation"),
        _trade(db, _at(13, 40), "loss", setup="liquidity_sweep"),
    ]
    cells = compute_time_edge(trades)["matrices"]["setup_type"]
    keyed = {(c["row"], c["phase"]): c["stats"]["total"] for c in cells}
    assert keyed == {
        ("liquidity_sweep", "ny_open"): 1,
        ("continuation", "ny_open"): 1,
        ("liquidity_sweep", "after_session"): 1,
    }


def test_ifvg_timeframe_matrix_skips_trades_without_timeframe(db: Session) -> None:
    trades = [_trade(db, _at(10, 5), "win", tf="1m"), _trade(db, _at(10, 6), "win")]
    cells = compute_time_edge(trades)["matrices"]["ifvg_timeframe"]
    assert [(c["row"], c["phase"]) for c in cells] == [("1m", "ny_open")]


def test_insights_require_min_sample_and_split_kinds(db: Session) -> None:
    good = [_trade(db, _at(10, m), "win", setup="liquidity_sweep") for m in range(MIN_SAMPLE)]
    bad = [_trade(db, _at(13, 40 + m), "loss", setup="continuation") for m in range(MIN_SAMPLE)]
    thin = [_trade(db, _at(15, 5), "win", setup="other")]
    insights = compute_time_edge([*good, *bad, *thin])["insights"]
    kinds = {(i["kind"], i["dimension"], i["row"], i["phase"]) for i in insights}
    assert ("strength", "Setup", "liquidity_sweep", "ny_open") in kinds
    assert ("weakness", "Setup", "continuation", "after_session") in kinds
    assert not any(i["row"] == "other" for i in insights)


def test_non_futures_trades_are_excluded(db: Session) -> None:
    fx = make_trade(db, status="closed", outcome="win", open_time=_at(10, 5), instrument_type="forex")
    assert compute_time_edge([fx])["by_ny_phase"]["ny_open"]["total"] == 0
