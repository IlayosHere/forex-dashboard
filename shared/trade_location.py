"""
shared/trade_location.py
------------------------
Single source of truth for the trade_location enum.

Used by:
  - api/schemas_trade.py  (field validation)
  - api/models.py         (reference for column values)
  - api/services/trade_stats_extended.py (breakdown labels)
"""
from __future__ import annotations

TRADE_LOCATION_VALUES: list[str] = ["home", "phone", "pc_outside"]

TRADE_LOCATION_LABELS: dict[str, str] = {
    "home": "Home",
    "phone": "Phone",
    "pc_outside": "PC Outside",
}
