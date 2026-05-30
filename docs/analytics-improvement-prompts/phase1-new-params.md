# Phase 1 — New Analytics Parameters

## What you are doing

You are adding 5 new analytics parameters to a forex signal dashboard's analytics system.
No database changes. No UI changes beyond `ui/lib/analyticsParamMeta.ts`. Pure Python analytics work.

---

## Mandatory first reads

Before writing a single line of code, read these files in order:

1. `analytics/AGENTS.md` — the full architecture, invariants, and common mistakes. Non-negotiable.
2. `docs/coding-standards.md` — file/function size limits, naming, type hints. All code must comply.
3. `analytics/params/temporal.py` — canonical example of a simple param file.
4. `analytics/params/candle_derived.py` — canonical example of a candle-dependent param file. Shows the `_find_signal_bar`, `_atr_pips_at_bar` helpers you MUST reuse.
5. `analytics/params/structure.py` — shows how to use `cached_h1`, `cached_d1` helpers.
6. `analytics/registry.py` — the `@register` decorator contract.
7. `analytics/candle_helpers.py` — all memoized helpers (`cached_atr`, `cached_h1`, `cached_d1`, `cached_ema20_h1`). Do not reinvent these.
8. `ui/lib/analyticsParamMeta.ts` + `ui/lib/analyticsParamMetaWhenSetup.ts` + `ui/lib/analyticsParamMetaMomentumCost.ts` — understand the existing metadata structure before adding entries.

---

## The 5 parameters to add

### 1. `kill_zone`

**File:** `analytics/params/temporal.py` (add to existing file — check line count stays ≤200)
**Strategies:** all (`*`, omit the `strategies=` argument)
**needs_candles:** False
**dtype:** `"str"`

**Logic:**
Convert `signal.candle_time` to New York time (use `ZoneInfo("America/New_York")`).
Map the NY hour to one of 6 buckets:

| Condition | Value |
|-----------|-------|
| 00:00–01:59 NY | `"dead_zone"` |
| 02:00–04:59 NY | `"asian_kz"` |
| 05:00–06:59 NY | `"london_kz"` |
| 07:00–09:59 NY | `"ny_am_kz"` |
| 10:00–12:59 NY | `"ny_lunch"` |
| 13:00–16:59 NY | `"ny_pm_kz"` |
| 17:00–23:59 NY | `"dead_zone"` |

Return `None` if `candle_time` is None or timezone conversion fails.

**UI metadata:** category `"when"`, label `"Kill Zone"`, description `"ICT kill zone at signal time (NY timezone)"`, unit `null`, bucketMap with human labels: `asian_kz` → `"Asian KZ"`, `london_kz` → `"London KZ"`, `ny_am_kz` → `"NY AM KZ"`, `ny_lunch` → `"NY Lunch"`, `ny_pm_kz` → `"NY PM KZ"`, `dead_zone` → `"Dead Zone"`.

---

### 2. `premium_discount_zone`

**File:** new file `analytics/params/structure_htf.py`
**Strategies:** all (`*`)
**needs_candles:** True
**dtype:** `"str"`

**Logic:**
1. Get the D1 resample using `cached_d1(candles)` from `analytics/candle_helpers.py`.
2. Find the signal bar index using `_find_signal_bar(candles, signal)` from `analytics/params/candle_derived.py`.
3. From the D1 frame, take the last completed day before the signal's date (not the current day — avoid lookahead).
4. `day_range = day_high - day_low`. If `day_range < 3 * pip_size(signal.symbol)`, return `None` (too narrow, unreliable).
5. `pos = (signal.entry - day_low) / day_range`
6. Map position:
   - `pos < 0.33` → `"discount"`
   - `pos > 0.67` → `"premium"`
   - else → `"equilibrium"`
7. Return `None` on any missing data.

**UI metadata:** category `"momentum"`, label `"Premium/Discount Zone"`, description `"Entry position within prior day's range: discount (lower 33%), equilibrium, or premium (upper 33%)"`, unit `null`, bucketMap: `discount` → `"Discount"`, `equilibrium` → `"Equilibrium"`, `premium` → `"Premium"`.

---

### 3. `liquidity_swept_prior`

**File:** new file `analytics/params/liquidity.py`
**Strategies:** all (`*`)
**needs_candles:** True
**dtype:** `"str"`

**Logic:**
1. Find signal bar index `idx` using `_find_signal_bar(candles, signal)`.
2. Look back 15 bars from the signal bar (bars `idx-15` to `idx-1` inclusive). If fewer than 15 bars available, use what's there but require at least 5.
3. Define "prior swing high" = max of the highs in `idx-25` to `idx-16` (the 10 bars before the lookback window). Define "prior swing low" = min of lows in that same outer window. If the outer window has fewer than 5 bars, return `None`.
4. Check if any bar in the lookback window (15 bars before signal) has:
   - `bar.low < prior_swing_low` → sellside sweep (`swept_sellside`)
   - `bar.high > prior_swing_high` → buyside sweep (`swept_buyside`)
5. If both occurred, use the one closest to the signal bar (most recent).
6. If neither: `"none"`.
7. Return `None` on any index/data issue.

**UI metadata:** category `"momentum"`, label `"Liquidity Swept Prior"`, description `"Whether a prior swing high/low was swept in the 15 bars before signal"`, unit `null`, bucketMap: `swept_buyside` → `"Swept Buyside"`, `swept_sellside` → `"Swept Sellside"`, `none` → `"No Sweep"`.

---

### 4. `sweep_to_signal_bars`

**File:** `analytics/params/liquidity.py` (same file as above)
**Strategies:** all (`*`)
**needs_candles:** True
**dtype:** `"int"`

**Logic:**
1. Same lookback logic as `liquidity_swept_prior` to find whether a sweep occurred and at which bar index.
2. If no sweep found, return `None`.
3. Return `idx - sweep_bar_idx` — number of bars between the sweep and the signal. Minimum 1.

**Note:** Share the sweep-detection helper between these two params as a private function `_find_sweep(candles, signal)` that returns `(sweep_type, sweep_bar_idx) | None`. Both params call it.

**UI metadata:** category `"momentum"`, label `"Bars Since Sweep"`, description `"Bars between the liquidity sweep and this signal (None if no sweep)"`, unit `"candles"`.

---

### 5. `resolution_candles_param`

**File:** `analytics/params/temporal.py` (add to existing file)
**Strategies:** all (`*`)
**needs_candles:** False
**dtype:** `"int"`

**Logic:**
Read `signal.resolution_candles` directly. Return `int(signal.resolution_candles)` if it is not None, else `None`.

**Important:** the registered name must be `"resolution_candles_param"` (not `"resolution_candles"`) to avoid colliding with the raw DB field name that appears in the enriched signal response.

**UI metadata:** category `"when"`, label `"Bars to Resolution"`, description `"How many bars from signal to TP/SL hit — fast resolutions indicate cleaner setups"`, unit `"candles"`.

---

## Parameter contract — invariants you MUST follow

Every param function signature: `def my_param(signal: Any, candles: pd.DataFrame | None) -> value | None`

1. Never raise. Return `None` for any missing data, NaN, division by zero, index error.
2. Cast numpy scalars: `bool(x)` not `x` for bools; `float(x)` for floats; `int(x)` for ints.
3. Never look forward past `signal.candle_time` in the candle DataFrame.
4. Use `cached_d1`, `cached_h1`, `cached_atr` from `analytics/candle_helpers.py` — never call resample inline.
5. Use `pip_size(signal.symbol)` from `shared/calculator.py` for all pip math.
6. Use `_find_signal_bar(candles, signal)` from `analytics/params/candle_derived.py` for bar index.
7. ≤ 10 distinct string values for `dtype="str"` params.

---

## Tests required

Tests go in `tests/`. Create:
- `tests/test_analytics_kill_zone.py`
- `tests/test_analytics_premium_discount.py`
- `tests/test_analytics_liquidity.py`
- `tests/test_analytics_resolution_candles.py`

Each file needs at minimum:
1. Happy path — returns expected bucket/value
2. `None` path — missing candles returns `None`
3. Edge case — boundary value (e.g. exactly at 50% for premium_discount → "equilibrium")
4. No-data path — signal bar not found in DataFrame returns `None`

Use this exact test scaffold (already established in the project):

```python
from unittest.mock import MagicMock
import pandas as pd
import numpy as np
import pytest

def _make_candles(n: int, base_price: float = 1.1000, freq: str = "15min") -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    return pd.DataFrame({
        "open":   [base_price] * n,
        "high":   [base_price + 0.0010] * n,
        "low":    [base_price - 0.0010] * n,
        "close":  [base_price] * n,
        "volume": [1000.0] * n,
    }, index=idx)

def _signal(**kwargs):
    m = MagicMock()
    m.strategy = kwargs.get("strategy", "fvg-impulse")
    m.symbol = kwargs.get("symbol", "EURUSD")
    m.direction = kwargs.get("direction", "BUY")
    m.candle_time = kwargs.get("candle_time", pd.Timestamp("2024-01-02 08:00", tz="UTC"))
    m.entry = kwargs.get("entry", 1.1000)
    m.sl = kwargs.get("sl", 1.0990)
    m.tp = kwargs.get("tp", 1.1010)
    m.risk_pips = kwargs.get("risk_pips", 10.0)
    m.spread_pips = kwargs.get("spread_pips", 1.0)
    m.signal_metadata = kwargs.get("signal_metadata", {})
    m.resolution_candles = kwargs.get("resolution_candles", None)
    return m
```

Float assertions: `pytest.approx(expected, abs=0.01)`.

---

## After writing code

Run: `python -m pytest tests/test_analytics_kill_zone.py tests/test_analytics_premium_discount.py tests/test_analytics_liquidity.py tests/test_analytics_resolution_candles.py -v --tb=short`

All tests must pass. Fix any failures before reporting done.

Also run the full analytics test suite to confirm no regressions:
`python -m pytest tests/ -k "analytics" -v --tb=short`

---

## Branch

Work on branch `feature/analytics-phase1`. Create it from `main`:
```
git checkout main
git pull
git checkout -b feature/analytics-phase1
```

Commit when all tests pass: one commit per param file + one commit for the metadata updates.

When all tests are green and the agent reports done, merge to `main` and delete the branch before starting Phase 2.
