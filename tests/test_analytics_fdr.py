"""Tests for Benjamini-Hochberg FDR correction in analytics/stats/report.py."""
from __future__ import annotations

import pytest

from analytics.stats.report import _apply_fdr


def _row(p_value: float | None, level: str | None) -> dict:
    return {"param_name": "x", "p_value": p_value, "level": level, "delta": 0.1}


def test_fdr_marks_confirmed_when_significant() -> None:
    rows = [_row(0.0001, "strong_positive"), _row(0.9, "hint_positive")]
    result = _apply_fdr(rows, q=0.10)
    assert result[0]["fdr_status"] == "confirmed"


def test_fdr_marks_exploratory_when_borderline() -> None:
    # p=0.04 at rank 1 of 1 gives threshold (1/1)*0.10 = 0.10 — passes BH.
    # Use two rows where the second one barely misses BH but passes Bonferroni.
    # With m=2, q=0.10: rank-1 threshold = 0.05, rank-2 threshold = 0.10.
    # p=0.06 at rank 2 → 0.06 <= 0.10 → confirmed (threshold for rank 2 is 0.10).
    # To get exploratory: both must fail BH. p=0.06 (rank2) and p=0.07 (rank1 after sort)?
    # Actually with p_sorted=[0.06, 0.07]: rank1→0.05, rank2→0.10.
    # 0.06 > 0.05 (miss) and 0.07 <= 0.10 (hit) → threshold_idx=1 → both confirmed.
    # Use p=[0.06, 0.12]: rank1(p=0.06)→0.05 miss, rank2(p=0.12)→0.10 miss → both exploratory.
    rows = [_row(0.06, "hint_positive"), _row(0.12, "hint_negative")]
    result = _apply_fdr(rows, q=0.10)
    assert result[0]["fdr_status"] == "exploratory"
    assert result[1]["fdr_status"] == "exploratory"


def test_fdr_marks_insufficient_when_none_level() -> None:
    rows = [_row(0.001, "none"), _row(None, "strong_positive"), _row(0.001, None)]
    result = _apply_fdr(rows, q=0.10)
    for row in result:
        assert row["fdr_status"] == "insufficient_data"


def test_fdr_empty_input() -> None:
    result = _apply_fdr([], q=0.10)
    assert result == []
