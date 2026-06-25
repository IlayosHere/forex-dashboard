"""
shared/market_holidays.py
--------------------------
Pure, offline NQ/MNQ market-holiday and closure data for the calendar feature.

Two kinds of entries, both scoped to CME Globex / NQ:
- Full closures and early-close half-days: a hand-maintained table sourced
  from CME's published calendar. No offline package models Globex correctly
  (it differs materially from NYSE/NASDAQ cash-equity hours), so this is
  verified directly against CME's holiday schedule.
- "Thin volume" days: US bank holidays (via the `holidays` package) on which
  NQ keeps trading normally hours-wise, but volume is typically very thin
  (e.g. Juneteenth, Columbus Day, Veterans Day) — these are NOT in the CME
  closure table because CME doesn't close or shorten hours for them, but a
  trader still needs the heads-up.

CME table verified against cmegroup.com/trading-hours.html for 2026. CME
finalizes each year's exact early-close times ~2 weeks ahead of the holiday
and publishes next year's table ahead of time — re-verify and extend this
table annually.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from typing import Any

import holidays


@dataclass(frozen=True)
class CmeClosure:
    name: str
    kind: str  # "full_close" | "early_close"
    close_time_et: str | None  # set when kind == "early_close"


# Equities halt ~12:15 PM CT (13:15 ET) on early-close days at CME Globex.
_EARLY_CLOSE_ET = "13:15"

CME_GLOBEX_HOLIDAYS: dict[date, CmeClosure] = {
    date(2026, 1, 1): CmeClosure("New Year's Day", "full_close", None),
    date(2026, 1, 19): CmeClosure("Martin Luther King Jr. Day", "early_close", _EARLY_CLOSE_ET),
    date(2026, 2, 16): CmeClosure("Presidents' Day", "early_close", _EARLY_CLOSE_ET),
    date(2026, 4, 3): CmeClosure("Good Friday", "full_close", None),
    date(2026, 5, 25): CmeClosure("Memorial Day", "early_close", _EARLY_CLOSE_ET),
    date(2026, 7, 3): CmeClosure("Independence Day (observed)", "early_close", _EARLY_CLOSE_ET),
    date(2026, 9, 7): CmeClosure("Labor Day", "early_close", _EARLY_CLOSE_ET),
    date(2026, 11, 26): CmeClosure("Thanksgiving Day", "early_close", _EARLY_CLOSE_ET),
    date(2026, 12, 24): CmeClosure("Christmas Eve", "early_close", _EARLY_CLOSE_ET),
    date(2026, 12, 25): CmeClosure("Christmas Day", "full_close", None),
    date(2026, 12, 31): CmeClosure("New Year's Eve", "early_close", _EARLY_CLOSE_ET),
}


@lru_cache(maxsize=16)
def _us_holidays_for_year(year: int) -> dict[date, str]:
    """Instantiate (and memoize) the US bank-holiday calendar for one year."""
    return dict(holidays.UnitedStates(years=[year]))


def cme_holidays_for_range(start: date, end: date) -> list[dict[str, Any]]:
    """CME Globex full-closures and early-closes in [start, end]."""
    results: list[dict[str, Any]] = []
    for day, closure in CME_GLOBEX_HOLIDAYS.items():
        if start <= day <= end:
            note = (
                "No signals will be generated today."
                if closure.kind == "full_close"
                else f"Trading halts at {closure.close_time_et} ET."
            )
            results.append({
                "date": day.isoformat(),
                "label": f"CME Globex — {closure.name}",
                "closure_type": closure.kind,
                "early_close_et": closure.close_time_et,
                "note": note,
            })
    return results


def us_thin_volume_days_for_range(start: date, end: date) -> list[dict[str, Any]]:
    """US bank holidays in [start, end] where NQ trades normal hours but thin.

    Excludes any date already covered by CME_GLOBEX_HOLIDAYS, since those days
    already carry a more specific full_close/early_close entry.
    """
    results: list[dict[str, Any]] = []
    for year in range(start.year, end.year + 1):
        for day, name in _us_holidays_for_year(year).items():
            if start <= day <= end and day not in CME_GLOBEX_HOLIDAYS:
                results.append({
                    "date": day.isoformat(),
                    "label": f"NQ — {name}",
                    "closure_type": "thin_volume",
                    "early_close_et": None,
                    "note": f"NQ trades normal hours, but volume is typically thin ({name}).",
                })
    return results
