# Phase 6 — Composite Setup Quality Score

## What you are doing

You are building a composite "setup quality score" that summarises multiple confirmed analytics edges into a single number shown on each signal card. A trader glancing at a new signal can instantly see whether it hits their known edges.

**Important prerequisite:** This phase should only be executed after Phase 1 and Phase 2 have been running long enough that the FDR summary (`GET /api/analytics/summary`) is returning at least 3 params with `fdr_status = "confirmed"`. If fewer than 3 confirmed params exist, the score is meaningless — delay this phase.

---

## Mandatory first reads

1. `docs/coding-standards.md`
2. `analytics/AGENTS.md` — especially the parameter contract and the enrichment pipeline
3. `analytics/stats/report.py` — understand `build_summary()` and `_rank_params()` — the score uses their output
4. `analytics/schemas.py` — you add a new response schema
5. `analytics/registry.py` — `get_params_for_strategy()` and `get_param_def()`
6. `analytics/enrichment.py` — `enrich_batch()` — you call it to compute params for a single signal
7. `api/routes/signals.py` — the signal routes; you may add the score to the signal response
8. `ui/components/SignalCard.tsx` — where you add the score badge
9. `ui/components/SignalDetail.tsx` — where you add the score breakdown
10. `ui/lib/types.ts` — the `Signal` interface you may extend

---

## Backend

### New module: `analytics/scoring.py`

This module computes a composite quality score from FDR-confirmed parameters.

```python
"""
analytics/scoring.py
--------------------
Rule-based composite setup quality score.

Score = sum of (weight_i * indicator_i) for confirmed params only.
- weight_i = effect size in percentage points (clipped to [-20, +20])
- indicator_i = +1 if signal falls in the "prefer" bucket,
                -1 if in the "avoid" bucket,
                 0 otherwise
Output: integer in range [-100, +100] approximately.
"""
```

**Key function:**

```python
def compute_score(
    signal: Any,
    strategy: str,
    candles: pd.DataFrame | None,
    confirmed_params: list[dict],   # from build_summary top_correlations where fdr_status="confirmed"
) -> dict:
    """
    Returns:
    {
        "score": int,                        # sum of weighted indicators
        "max_possible": int,                 # sum of abs weights (for normalisation)
        "contributing": list[dict],          # params that fired with nonzero indicator
        "explanation": str,                  # human-readable e.g. "3 of 5 edges matched"
    }
    """
```

**Implementation rules:**
- For each confirmed param, call its registered function to get the current value.
- Compare value to `best_bucket` from the summary row:
  - If value matches `best_bucket` and `delta > 0` → `indicator = +1`
  - If value matches `best_bucket` and `delta < 0` → `indicator = -1`
  - Otherwise → `indicator = 0`
- `weight = int(round(abs(delta) * 100))` clipped to `[2, 20]`.
- `score = sum(weight_i * indicator_i)`
- `max_possible = sum(weight_i for all confirmed params)`
- `contributing = [{param_name, bucket, indicator, weight}]` for params where `indicator != 0`
- `explanation = f"{pos_count} edge(s) matched, {neg_count} violated, {neutral_count} neutral"`

Only params with `fdr_status = "confirmed"` contribute. Never include exploratory params.

### New endpoint

Add to `analytics/routes_stats.py`:

```
GET /api/analytics/score/{signal_id}
  ?strategy=  (required)
```

1. Load the signal from DB by `signal_id`. Return 404 if not found.
2. Call `build_summary()` to get the confirmed params (reuse the enriched-batch cache).
3. Filter `top_correlations` to `fdr_status = "confirmed"`.
4. Fetch candles for the signal's symbol at its strategy's interval (use `get_app_cache()`).
5. Call `compute_score(signal, strategy, candles, confirmed_params)`.
6. Return as `ScoreResponse`.

**New schema** (add to `analytics/schemas.py`):

```python
class ScoreContributor(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    param_name: str
    bucket: str | None
    indicator: int       # +1, -1, or 0
    weight: int

class ScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    signal_id: str
    score: int
    max_possible: int
    contributing: list[ScoreContributor]
    explanation: str
    confirmed_params_used: int
```

---

## Frontend

### Update `ui/components/SignalCard.tsx`

Add a small score badge to the signal card. Only show it if there are ≥ 3 confirmed params (i.e., `max_possible > 0`).

Display: a compact badge showing the score. Examples:
- `+18 / 40` in green if score > 0
- `−12 / 40` in red if score < 0
- `0 / 40` in grey if neutral

Fetch the score lazily — don't fetch on every card render. Only fetch when the card is expanded or hovered. Use `useCallback` + manual fetch triggered by user interaction, not on mount (there could be many signal cards).

### Update `ui/components/SignalDetail.tsx`

In the detail view (when a signal card is expanded or the detail panel is open), show the full score breakdown:

```
Setup Quality Score: +18 / 40

Matched edges:
  ✓ Kill Zone — NY AM KZ (+8)
  ✓ Wick Penetration — Q5: high (+6)
  ✓ H1 Trend — WITH (+4)

Violated:
  ✗ Premium/Discount — Premium (−8 expected)

Neutral:
  · Session Label (no strong edge in this param)
```

This uses the `contributing` list from the `ScoreResponse`. Style: compact, dark theme, clear hierarchy.

### New hook: `ui/lib/useSignalScore.ts`

```typescript
export function useSignalScore(signalId: string, strategy: string): {
  data: ScoreResponse | null;
  loading: boolean;
  fetch: () => void;   // call this to trigger the fetch
}
```

Does NOT fetch on mount. Exposes a `fetch()` function the component calls when the user opens the detail.

---

## Tests required

### Backend test: `tests/test_analytics_scoring.py`

```python
def test_score_positive_when_all_edges_matched():
    # All confirmed params return their "prefer" bucket value → score > 0

def test_score_negative_when_edges_violated():
    # All confirmed params return their "avoid" bucket value → score < 0

def test_score_zero_when_no_confirmed_params():
    # Empty confirmed_params list → score=0, max_possible=0

def test_contributing_only_includes_nonzero_indicators():
    # Neutral params (indicator=0) don't appear in contributing list

def test_score_explanation_format():
    # explanation matches "X edge(s) matched, Y violated, Z neutral"
```

Run: `python -m pytest tests/test_analytics_scoring.py -v --tb=short`
Full: `python -m pytest tests/ -k "analytics" -v --tb=short`

Frontend: `cd ui && npx tsc --noEmit`

---

## Branch

Work on `feature/analytics-phase6`. Create from `main` (Phases 4 and 5 must both be merged to main first):
```
git checkout main
git pull
git checkout -b feature/analytics-phase6
```

Three commits: scoring module + tests, endpoint + schema, frontend badge + detail + hook.

When all tests are green and the agent reports done, merge to `main` and delete the branch.
