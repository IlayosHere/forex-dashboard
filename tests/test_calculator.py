"""
tests/test_calculator.py
------------------------
Unit tests for shared/calculator.py: calculate_lot_size (futures contracts).
"""
from __future__ import annotations

from shared.calculator import calculate_lot_size

# ---------------------------------------------------------------------------
# calculate_lot_size — MNQ (symbol-based routing)
# ---------------------------------------------------------------------------


def test_calc_lot_size_futures_mnq() -> None:
    # MNQ: $2/pt — $500 risk / (50 pts * $2) = 5 contracts
    result = calculate_lot_size(
        symbol="MNQ", entry=20000, sl_points=50.0,
        account_balance=50_000, risk_percent=1.0,
        instrument_type="futures",
    )
    assert result["risk_usd"] == 500.0
    assert result["lot_size"] == 5
    assert result["instrument_type"] == "futures"


def test_calc_lot_size_with_tp_gives_rr() -> None:
    result = calculate_lot_size(
        symbol="MNQ", entry=20000, sl_points=25.0,
        account_balance=50_000, risk_percent=1.0, tp_points=50.0,
    )
    assert result["rr"] == 2.0


def test_calc_lot_size_futures_zero_sl() -> None:
    result = calculate_lot_size(
        symbol="MNQ", entry=20000, sl_points=0,
        account_balance=50_000, risk_percent=1.0,
        instrument_type="futures",
    )
    assert result["lot_size"] == 1


def test_calc_lot_size_futures_min_one_contract() -> None:
    result = calculate_lot_size(
        symbol="MNQ", entry=20000, sl_points=500.0,
        account_balance=10_000, risk_percent=0.5,
        instrument_type="futures",
    )
    assert result["lot_size"] >= 1


# ---------------------------------------------------------------------------
# calculate_lot_size — MES (symbol-based, same instrument_type="futures")
# ---------------------------------------------------------------------------


def test_calc_lot_size_futures_mes() -> None:
    # MES: $5/pt — $500 risk / (20 pts * $5) = 5 contracts
    result = calculate_lot_size(
        symbol="MES", entry=5000, sl_points=20.0,
        account_balance=50_000, risk_percent=1.0,
        instrument_type="futures",
    )
    assert result["risk_usd"] == 500.0
    assert result["lot_size"] == 5
    assert result["instrument_type"] == "futures"


def test_calc_lot_size_futures_mes_larger_sl() -> None:
    # $500 risk / (50 pts * $5) = 2 contracts
    result = calculate_lot_size(
        symbol="MES", entry=5000, sl_points=50.0,
        account_balance=50_000, risk_percent=1.0,
        instrument_type="futures",
    )
    assert result["lot_size"] == 2


def test_calc_lot_size_futures_mes_zero_sl() -> None:
    result = calculate_lot_size(
        symbol="MES", entry=5000, sl_points=0,
        account_balance=50_000, risk_percent=1.0,
        instrument_type="futures",
    )
    assert result["lot_size"] == 1


def test_calc_lot_size_futures_mes_min_one_contract() -> None:
    result = calculate_lot_size(
        symbol="MES", entry=5000, sl_points=500.0,
        account_balance=5_000, risk_percent=0.5,
        instrument_type="futures",
    )
    assert result["lot_size"] >= 1


def test_calc_lot_size_futures_mes_vs_mnq_ratio() -> None:
    """Same risk/SL: MES needs fewer contracts than MNQ (MES=$5/pt vs MNQ=$2/pt)."""
    mnq = calculate_lot_size(
        symbol="MNQ", entry=20000, sl_points=20.0,
        account_balance=50_000, risk_percent=1.0,
        instrument_type="futures",
    )
    mes = calculate_lot_size(
        symbol="MES", entry=5000, sl_points=20.0,
        account_balance=50_000, risk_percent=1.0,
        instrument_type="futures",
    )
    # MNQ: 500 / (20 * 2) = 12 contracts; MES: 500 / (20 * 5) = 5 contracts
    assert mes["lot_size"] < mnq["lot_size"]


def test_calc_lot_size_unknown_symbol_falls_back_to_default_multiplier() -> None:
    result = calculate_lot_size(
        symbol="NQ", entry=20000, sl_points=50.0,
        account_balance=50_000, risk_percent=1.0,
        instrument_type="futures",
    )
    assert result["lot_size"] >= 1
