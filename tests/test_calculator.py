"""
tests/test_calculator.py
------------------------
Unit tests for shared/calculator.py: pip_size, pip_value_per_lot, calculate_lot_size.
"""
from __future__ import annotations

import pytest

from shared.calculator import calculate_lot_size, pip_size, pip_value_per_lot


# ---------------------------------------------------------------------------
# pip_size
# ---------------------------------------------------------------------------


def test_pip_size_jpy_pair_returns_001() -> None:
    assert pip_size("USDJPY") == 0.01


def test_pip_size_non_jpy_pair_returns_00001() -> None:
    assert pip_size("EURUSD") == 0.0001


def test_pip_size_slash_separated_jpy() -> None:
    assert pip_size("USD/JPY") == 0.01


def test_pip_size_slash_separated_non_jpy() -> None:
    assert pip_size("EUR/USD") == 0.0001


def test_pip_size_lowercase_input() -> None:
    assert pip_size("gbpjpy") == 0.01


def test_pip_size_cross_pair_no_jpy() -> None:
    assert pip_size("EURGBP") == 0.0001


# ---------------------------------------------------------------------------
# pip_value_per_lot
# ---------------------------------------------------------------------------


def test_pip_value_usd_quote_returns_10() -> None:
    assert pip_value_per_lot("EURUSD", 1.0850) == 10.0


def test_pip_value_gbpusd_returns_10() -> None:
    assert pip_value_per_lot("GBPUSD", 1.2700) == 10.0


def test_pip_value_usdjpy_calculated() -> None:
    result = pip_value_per_lot("USDJPY", 150.0)
    expected = (100_000 * 0.01) / 150.0
    assert result == pytest.approx(expected)


def test_pip_value_usdchf_calculated() -> None:
    result = pip_value_per_lot("USDCHF", 0.9100)
    expected = (100_000 * 0.0001) / 0.9100
    assert result == pytest.approx(expected)


def test_pip_value_cross_pair_fallback_10() -> None:
    assert pip_value_per_lot("EURGBP", 0.8500) == 10.0


# ---------------------------------------------------------------------------
# calculate_lot_size — forex
# ---------------------------------------------------------------------------


def test_calc_lot_size_basic_forex() -> None:
    result = calculate_lot_size(
        symbol="EURUSD", entry=1.0850, sl_pips=30.0,
        account_balance=10_000, risk_percent=1.0,
    )
    assert result["risk_usd"] == 100.0
    assert result["lot_size"] == 0.33
    assert result["sl_pips"] == 30.0
    assert result["rr"] is None
    assert result["instrument_type"] == "forex"


def test_calc_lot_size_with_tp_gives_rr() -> None:
    result = calculate_lot_size(
        symbol="EURUSD", entry=1.0850, sl_pips=25.0,
        account_balance=10_000, risk_percent=1.0, tp_pips=50.0,
    )
    assert result["rr"] == 2.0


def test_calc_lot_size_zero_sl_returns_minimum() -> None:
    result = calculate_lot_size(
        symbol="EURUSD", entry=1.0850, sl_pips=0,
        account_balance=10_000, risk_percent=1.0,
    )
    assert result["lot_size"] == 0.01
    assert result["risk_usd"] == 0.0


# ---------------------------------------------------------------------------
# calculate_lot_size — futures
# ---------------------------------------------------------------------------


def test_calc_lot_size_futures_mnq() -> None:
    result = calculate_lot_size(
        symbol="MNQ", entry=20000, sl_pips=50.0,
        account_balance=50_000, risk_percent=1.0,
        instrument_type="futures_mnq",
    )
    assert result["risk_usd"] == 500.0
    assert result["lot_size"] == 5
    assert result["instrument_type"] == "futures_mnq"


def test_calc_lot_size_futures_zero_sl() -> None:
    result = calculate_lot_size(
        symbol="MNQ", entry=20000, sl_pips=0,
        account_balance=50_000, risk_percent=1.0,
        instrument_type="futures_mnq",
    )
    assert result["lot_size"] == 1


def test_calc_lot_size_futures_min_one_contract() -> None:
    result = calculate_lot_size(
        symbol="MNQ", entry=20000, sl_pips=500.0,
        account_balance=10_000, risk_percent=0.5,
        instrument_type="futures_mnq",
    )
    assert result["lot_size"] >= 1
