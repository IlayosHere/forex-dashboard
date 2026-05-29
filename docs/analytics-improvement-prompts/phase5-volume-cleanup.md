# Phase 5 — Volume Param Cleanup + Bug Fix

## What you are doing

Three targeted cleanups in the analytics params layer:

1. **Merge volume params** — `relative_volume`, `volume_percentile`, and `volume_regime` currently measure nearly the same thing. Replace them with a single `volume_regime` param that is session-normalized (so it doesn't just reflect "NY has more volume than Asia").
2. **Fix `h1_fvg_contains_entry` H1 max age bug** — the param uses `MAX_FVG_AGE=15` which was calibrated for M15 bars. On H1 bars that's 15 hours instead of ~3.75 hours. The correct value is 4 H1 bars.
3. **Remove deprecated params from the UI metadata** — clean up `analyticsParamMeta` so the removed params don't appear in dropdowns.

---

## Mandatory first reads

1. `docs/coding-standards.md`
2. `analytics/AGENTS.md` — section "Common mistakes" and the parameter contract
3. `analytics/params/volume.py` — the three volume params you are replacing
4. `analytics/params/candle_derived.py` — `_volume_at_bar`, `_find_signal_bar` helpers you will reuse
5. `analytics/params/fvg_impulse_5m.py` — contains `h1_fvg_contains_entry` with the bug
6. `analytics/registry.py` — understand how `@register` and `unregister` work (check if an unregister exists; if not, just remove the `@register` decorator and delete the function)
7. `ui/lib/analyticsParamMeta.ts` and its split files — remove deprecated entries
8. `analytics/candle_helpers.py` — `cached_h1` helper you will use

---

## Change 1: Replace 3 volume params with session-normalized `volume_regime`

### Remove from `analytics/params/volume.py`

Delete the `@register` decorators and function bodies for:
- `relative_volume`
- `volume_percentile`

Keep the file. Rename it clearly in the docstring.

### Rewrite `volume_regime`

The new `volume_regime` must be session-normalized:

**Logic:**
1. Get `bar_volume` using `_volume_at_bar(candles, signal)`. If `None`, return `None`.
2. Find signal bar index `idx` using `_find_signal_bar(candles, signal)`.
3. Determine the session for the signal bar: convert `signal.candle_time` to NY time (use `ZoneInfo("America/New_York")`). Get the NY hour.
4. Map to session group:
   - Hours 0–6 → `"asian"`
   - Hours 7–12 → `"london"`  
   - Hours 13–20 → `"ny"`
   - Hours 21–23 → `"asian"` (late session / early Asian)
5. For the prior 50 bars, filter to only bars whose timestamp falls in the **same session group** as the signal. Require at least 10 same-session bars; if fewer, fall back to using all prior 50 bars without session filtering.
6. Compute `mean_vol` over those session-filtered bars.
7. `rv = bar_volume / mean_vol` if `mean_vol > 0` else return `None`.
8. Bucket:
   - `rv < 0.7` → `"low"`
   - `rv > 1.5` → `"high"`
   - else → `"normal"`

**dtype:** `"str"`
**needs_candles:** True
**strategies:** all (`*`)
**registered name:** `"volume_regime"` (same as before — the UI metadata key doesn't change)

### Update UI metadata

In `ui/lib/analyticsParamMetaMomentumCost.ts` (or wherever volume params are defined):
- Remove entries for `relative_volume` and `volume_percentile`
- Update `volume_regime` description to: `"Session-normalized volume: compares signal bar volume to bars in the same session window"`

---

## Change 2: Fix `h1_fvg_contains_entry` H1 max age

**File:** `analytics/params/fvg_impulse_5m.py`

Find the call to `age_and_prune_fvgs`. The current code uses a constant `MAX_FVG_AGE` that is calibrated for M15 bars (value = 15). On H1 resampled data, 15 bars = 15 hours instead of the intended ~3.75 hours.

The comment in the file already notes `_H1_MAX_FVG_AGE = 4` as the correct value.

**Fix:** check whether `age_and_prune_fvgs` accepts a `max_age` parameter. 
- If yes: pass `max_age=4` when calling it on H1 data.
- If no: create a local wrapper or patch the call to limit FVG age to 4 H1 bars. Do not modify `age_and_prune_fvgs` itself if it's used elsewhere with M15 expectations — add a keyword argument with a default that preserves existing behavior.

Read the function signature in `strategies/fvg_impulse/data.py` before deciding the approach.

---

## Change 3: Remove deprecated params from UI metadata

Remove these keys from `ui/lib/analyticsParamMetaMomentumCost.ts` (or whichever file contains them):
- `relative_volume`
- `volume_percentile`

Do a global search in `ui/` for any references to `relative_volume` or `volume_percentile` (in component code, hooks, or pages) and remove those references. These params will no longer appear in API responses so any hardcoded references will break at runtime.

---

## Tests required

### Volume param test: `tests/test_analytics_volume_regime_v2.py`

```python
def test_volume_regime_high_in_same_session():
    # Signal in NY session, signal bar volume 2x session mean → "high"

def test_volume_regime_low_volume():
    # Signal bar volume 0.5x session mean → "low"

def test_volume_regime_no_volume_column():
    # Candles without volume column → None

def test_volume_regime_falls_back_when_few_session_bars():
    # Only 5 same-session bars in prior 50 → falls back to all 50 bars

def test_volume_regime_none_when_no_candles():
    # candles=None → None
```

### H1 FVG fix test: add one test to `tests/test_analytics_fvg_impulse_5m.py` (existing file)

```python
def test_h1_fvg_contains_entry_uses_h1_max_age():
    # Build candles where an H1 FVG is older than 4 H1 bars (but <15)
    # Assert h1_fvg_contains_entry returns False (old FVG pruned)
    # This verifies the fix is applied
```

Run: `python -m pytest tests/test_analytics_volume_regime_v2.py -v --tb=short`
Run: `python -m pytest tests/test_analytics_fvg_impulse_5m.py -v --tb=short`
Full: `python -m pytest tests/ -k "analytics" -v --tb=short`

Frontend: `cd ui && npx tsc --noEmit`

---

## Branch

Work on `feature/analytics-phase5`. Create from `main` (Phase 2 must be merged to main first — Phase 5 runs in parallel with Phase 3 and 4, not after them):
```
git checkout main
git pull
git checkout -b feature/analytics-phase5
```

Two commits: one for Python changes (volume + bug fix), one for TS metadata cleanup.

When all tests are green and the agent reports done, merge to `main` and delete the branch. This can be merged independently — it does not need to wait for Phase 3 or 4.
