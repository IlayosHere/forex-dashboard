"""
shared/economic_calendar.py
-----------------------------
Pure, offline, recurring high/medium-impact USD economic-event schedule for the
backtest news-awareness feature. Same conventions as shared/market_holidays.py:
hand-maintained tables, no network dependency, correct for arbitrary date ranges
including past dates.

Two kinds of entries:
- NFP (Non-Farm Payrolls): computed by rule, not hand-maintained — it is always
  the first Friday of the month, no exceptions.
- FOMC / CPI / PPI / GDP: hand-maintained per-year tables sourced from
  federalreserve.gov, bls.gov, and bea.gov release schedules. Unlike NFP, these
  do NOT follow a clean weekday formula (e.g. CPI is "around the second week"
  but the exact day varies and is set by BLS each year), so a rule-based
  approximation would silently produce wrong dates — these must be hand-entered
  and verified against the source.

Known gaps (intentional — dates are only added once confirmed against a
source; never guessed):
- The Oct 2025-Feb 2026 window was scrambled by a 43-day federal government
  shutdown: BLS canceled or delayed several CPI/PPI releases, and BEA canceled
  the Q3 2025 GDP advance estimate outright. Some 2025 CPI/PPI/GDP dates in
  that window are entries for the *actual* delayed release day, not the
  originally-scheduled day.
- 2025 CPI: only the two shutdown-affected exceptions are confirmed (the
  rest of 2025's months were not individually re-verified for this table).
- 2025 GDP: Q1/Q2 advance-estimate dates are not confirmed, omitted.
- 2026 PPI/GDP: only confirmed through ~mid-2026 — extend as BLS/BEA publish
  later dates.

Re-verify and extend all four hand-maintained tables annually, same as
CME_GLOBEX_HOLIDAYS in shared/market_holidays.py.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

# ---------------------------------------------------------------------------
# Hand-maintained tables — verified against federalreserve.gov / bls.gov / bea.gov
# ---------------------------------------------------------------------------

FOMC_DECISION_DATES: dict[int, list[date]] = {
    2025: [
        date(2025, 1, 29), date(2025, 3, 19), date(2025, 5, 7), date(2025, 6, 18),
        date(2025, 7, 30), date(2025, 9, 17), date(2025, 10, 29), date(2025, 12, 10),
    ],
    2026: [
        date(2026, 1, 28), date(2026, 3, 18), date(2026, 4, 29), date(2026, 6, 17),
        date(2026, 7, 29), date(2026, 9, 16), date(2026, 10, 28), date(2026, 12, 9),
    ],
}

CPI_RELEASE_DATES: dict[int, list[date]] = {
    # Only shutdown-affected exceptions confirmed for 2025 — see module docstring.
    2025: [date(2025, 10, 24), date(2025, 12, 18)],
    2026: [
        date(2026, 1, 13), date(2026, 2, 13), date(2026, 3, 11), date(2026, 4, 10),
        date(2026, 5, 12), date(2026, 6, 10), date(2026, 7, 14), date(2026, 8, 12),
        date(2026, 9, 11), date(2026, 10, 14), date(2026, 11, 10), date(2026, 12, 10),
    ],
}

PPI_RELEASE_DATES: dict[int, list[date]] = {
    2025: [
        date(2025, 1, 14), date(2025, 2, 13), date(2025, 3, 13), date(2025, 4, 11),
        date(2025, 6, 12), date(2025, 7, 16), date(2025, 8, 14), date(2025, 9, 10),
        date(2025, 11, 25), date(2025, 12, 11),
    ],
    2026: [
        date(2026, 1, 14), date(2026, 1, 30), date(2026, 2, 27), date(2026, 3, 18),
        date(2026, 4, 14), date(2026, 5, 13), date(2026, 6, 11), date(2026, 7, 15),
    ],
}

GDP_RELEASE_DATES: dict[int, list[date]] = {
    2025: [date(2025, 12, 23)],  # Q3 2025 "initial estimate" — advance estimate was canceled
    2026: [date(2026, 2, 20), date(2026, 4, 30), date(2026, 5, 28)],
}

# ---------------------------------------------------------------------------
# Rule-based: NFP is always the first Friday of the month, no exceptions.
# ---------------------------------------------------------------------------


def _first_friday(year: int, month: int) -> date:
    d = date(year, month, 1)
    offset = (4 - d.weekday()) % 7  # Mon=0 ... Fri=4
    return d + timedelta(days=offset)


def _nfp_dates_for_year(year: int) -> list[date]:
    return [_first_friday(year, month) for month in range(1, 13)]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_EVENTS: tuple[tuple[str, str, dict[int, list[date]] | None], ...] = (
    ("Non-Farm Payrolls", "high", None),  # NFP handled via _nfp_dates_for_year
    ("FOMC Rate Decision", "high", FOMC_DECISION_DATES),
    ("CPI", "high", CPI_RELEASE_DATES),
    ("PPI", "medium", PPI_RELEASE_DATES),
    ("GDP", "medium", GDP_RELEASE_DATES),
)


def economic_events_for_range(start: date, end: date) -> list[dict[str, Any]]:
    """Recurring high/medium-impact USD economic events in [start, end].

    Only events present in the hand-maintained tables (or matching the NFP
    rule) are returned — there is no separate impact filter, since low-impact
    events are never added to this table in the first place.
    """
    results: list[dict[str, Any]] = []
    for year in range(start.year, end.year + 1):
        for day in _nfp_dates_for_year(year):
            if start <= day <= end:
                results.append(_to_entry(day, "Non-Farm Payrolls", "high"))
    for name, impact, table in _EVENTS:
        if table is None:
            continue
        for year in range(start.year, end.year + 1):
            for day in table.get(year, []):
                if start <= day <= end:
                    results.append(_to_entry(day, name, impact))
    results.sort(key=lambda r: r["date"])
    return results


def _to_entry(day: date, name: str, impact: str) -> dict[str, Any]:
    return {
        "date": day.isoformat(),
        "name": name,
        "impact": impact,
        "currency": "USD",
    }


def coverage_through() -> date:
    """Latest date through which ALL hand-maintained tables (FOMC, CPI, PPI,
    GDP) have confirmed entries — i.e. the most-limiting table's last date.

    NFP is excluded since it's rule-based and never runs out. A date after
    this is not "confirmed no news" — it just means at least one of the four
    hand-maintained tables hasn't been extended that far yet. Re-derive
    automatically as tables are extended; never hardcode this date.
    """
    hand_maintained = (FOMC_DECISION_DATES, CPI_RELEASE_DATES, PPI_RELEASE_DATES, GDP_RELEASE_DATES)
    latest_per_table = (max(d for year_dates in table.values() for d in year_dates) for table in hand_maintained)
    return min(latest_per_table)
