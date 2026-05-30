# Phase 3 — Regime Detection

## What you are doing

You are adding a regime-shift detection feature. It answers the question: "is my strategy still working, or has the win rate changed significantly in recent trades?"

Two deliverables:
1. **Backend** — new endpoint `GET /api/analytics/regime` that compares the last 30 resolved signals vs the prior 30 and flags significant divergence.
2. **Frontend** — a `RegimeBanner` component wired into the statistics page that shows a green/amber/red health indicator per strategy.

---

## Mandatory first reads

1. `docs/coding-standards.md` — all code must comply.
2. `analytics/enrichment.py` — read `fetch_resolved()` to understand how resolved signals are queried.
3. `analytics/routes_stats.py` — understand the existing analytics route structure before adding a new one.
4. `analytics/schemas.py` — add a new response schema here.
5. `api/main.py` — understand how routers are mounted.
6. `ui/app/statistics/page.tsx` — you will add the banner above the existing sections.
7. `ui/components/stats/` — look at existing stat components for style patterns.
8. `ui/lib/types.ts` (or wherever frontend types live) — add the new type here.

---

## Backend

### New endpoint

Add to `analytics/routes_stats.py`:

```
GET /api/analytics/regime
  ?strategy=  (required)
  ?symbol=    (optional)
```

**Response schema** (add to `analytics/schemas.py`):

```python
class RegimeWindowStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    n: int
    win_rate: float
    wins: int

class RegimeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    strategy: str
    symbol: str | None
    recent: RegimeWindowStats       # last 30 resolved
    prior: RegimeWindowStats        # prior 30 resolved
    delta: float                    # recent.win_rate - prior.win_rate
    z_score: float | None           # two-proportion z, None if insufficient data
    status: str                     # "healthy" | "warning" | "degraded" | "insufficient_data"
    sufficient_data: bool           # True if both windows have >= 20 signals
```

**Status logic:**
- `sufficient_data = False` if either window has < 20 signals → `status = "insufficient_data"`
- Otherwise compute two-proportion z-score: `z = (p1 - p2) / sqrt(p_pool * (1-p_pool) * (1/n1 + 1/n2))` where `p_pool = (w1+w2)/(n1+n2)`
- `abs(z) < 1.65` → `"healthy"`
- `1.65 ≤ abs(z) < 2.0` → `"warning"` (directionally concerning but not definitive)
- `abs(z) ≥ 2.0` → `"degraded"` if `delta < 0` else `"healthy"` (significant but improving is fine)

**Implementation notes:**
- Call `fetch_resolved()` with `limit=60` to get the 60 most recent resolved signals for the strategy/symbol.
- Sort by `candle_time` descending. First 30 = recent window. Next 30 = prior window.
- If fewer than 40 total resolved signals exist, return `sufficient_data=False`.
- Extract this logic into a private function `_compute_regime(signals)` in the route file.
- The route handler must stay ≤ 40 lines. Extract helpers.

**Auth:** wrap with `get_current_user` dependency (same pattern as existing analytics routes).

---

## Frontend

### New component: `ui/components/stats/RegimeBanner.tsx`

Props:
```typescript
interface RegimeBannerProps {
  strategy: string;
  symbol?: string;
}
```

The component fetches `GET /api/analytics/regime?strategy=...&symbol=...` on mount (no polling needed — this is for display only).

Display rules:
- `status = "insufficient_data"` → render nothing (return null). Don't clutter the page before there's enough data.
- `status = "healthy"` → subtle green bar: `"Strategy performing as expected (recent 30 trades: XX% win rate)"`
- `status = "warning"` → amber bar: `"Win rate shift detected — recent 30 trades: XX% vs prior 30: XX%. Monitor closely."`
- `status = "degraded"` → red bar: `"Significant win rate decline — recent 30 trades: XX% vs prior 30: XX%. Review conditions."`

Style: a single horizontal pill/banner. Dark background (match project dark theme). Left-colored border (green/amber/red). Compact — not an alert modal.

### Wire into statistics page

In `ui/app/statistics/page.tsx`, add the `RegimeBanner` above the first `<section id="overview">`.
The statistics page already has a `ctx` object with `ctx.context.strategy` — pass that as the `strategy` prop.
If `ctx.context.strategy` is empty or "all", don't render the banner (regime is per-strategy, not aggregate).

### New hook: `ui/lib/useRegime.ts`

```typescript
export interface RegimeResult { ... }
export function useRegime(strategy: string, symbol?: string): {
  data: RegimeResult | null;
  loading: boolean;
  error: string | null;
}
```

Fetch once on mount. No polling. Clean up with AbortController.

---

## Type safety

- Add `RegimeResult` interface to `ui/lib/types.ts` mirroring the backend `RegimeResponse`.
- No `any`. No type assertions.

---

## Tests required

### Backend test: `tests/test_analytics_regime.py`

```python
def test_regime_healthy_when_similar_win_rates():
    # Two windows both ~50% win rate → status="healthy"

def test_regime_degraded_when_recent_worse():
    # Recent window 30% win rate, prior 65% → status="degraded"

def test_regime_insufficient_data_when_few_signals():
    # Only 15 total signals → sufficient_data=False, status="insufficient_data"

def test_regime_warning_zone():
    # Borderline z-score 1.7 → status="warning"
```

Run: `python -m pytest tests/test_analytics_regime.py -v --tb=short`
Full suite: `python -m pytest tests/ -k "analytics" -v --tb=short`

### Frontend
Run `cd ui && npx tsc --noEmit` — no TypeScript errors.

---

## Branch

Work on `feature/analytics-phase3`. Create from `main` (Phase 2 must be merged to main first):
```
git checkout main
git pull
git checkout -b feature/analytics-phase3
```

Two commits: one for backend (endpoint + schema + tests), one for frontend (hook + component + page wire-in).

When all tests are green and the agent reports done, merge to `main` and delete the branch before starting Phase 4.
