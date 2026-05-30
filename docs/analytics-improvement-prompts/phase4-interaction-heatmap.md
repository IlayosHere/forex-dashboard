# Phase 4 — Interaction Heatmap Page

## What you are doing

You are building a new sub-page inside the statistics section that shows 2D win-rate heatmaps for pairs of analytics parameters. This answers the question: "when condition A AND condition B are both true, what's my win rate?" — something the univariate analysis cannot answer.

The page structure mirrors how the journal has sub-pages (`/journal`, `/journal/new`, `/journal/[id]`).

---

## Mandatory first reads

1. `docs/coding-standards.md` — all code must comply. Page max 300 lines, components max 250.
2. `analytics/routes_stats.py` — existing analytics route file where you add the new endpoint.
3. `analytics/enrichment.py` — `fetch_resolved()` and `enrich_batch()` — the new endpoint reuses these.
4. `analytics/schemas.py` — add new response schema here.
5. `analytics/stats/filters.py` — `category_split()` and `quintile_split()` — reuse for bucketing.
6. `ui/app/statistics/page.tsx` — understand how the statistics page is structured.
7. `ui/app/journal/` — look at how journal sub-pages are structured for navigation patterns.
8. `ui/lib/analyticsParamMeta.ts` — you need param labels and bucket labels for the axis titles.
9. `ui/components/stats/` — existing stats components for style reference.

---

## Backend

### New endpoint

Add to `analytics/routes_stats.py`:

```
GET /api/analytics/interaction
  ?strategy=   (required)
  ?param_a=    (required — first parameter name)
  ?param_b=    (required — second parameter name)
  ?symbol=     (optional)
```

**Response schema** (add to `analytics/schemas.py`):

```python
class InteractionCell(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    bucket_a: str
    bucket_b: str
    wins: int
    losses: int
    total: int
    win_rate: float | None   # None if total < 15 (sparse cell)

class InteractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    strategy: str
    param_a: str
    param_b: str
    buckets_a: list[str]     # ordered list of param_a bucket labels
    buckets_b: list[str]     # ordered list of param_b bucket labels
    cells: list[InteractionCell]
    total_signals: int
    overall_win_rate: float
```

**Implementation:**

1. Validate that `param_a` and `param_b` are both registered params for the requested strategy. Return 422 if not.
2. Call `fetch_resolved()` + `enrich_batch()` (reuse the existing cache pattern from `routes_stats.py`).
3. For each enriched signal, read `params[param_a]` and `params[param_b]`.
4. Bucket each signal using:
   - `category_split` for `dtype in ("str", "bool")`
   - `quintile_split` for `dtype in ("float", "int")`
   Use the param's dtype from `get_param_def()`.
5. Build a 2D count grid: `grid[(bucket_a_label, bucket_b_label)] = [wins, losses]`.
6. For each cell: if `total < 15`, set `win_rate = None` (sparse — don't show).
7. Return all cells (including sparse ones with `win_rate=None`) so the frontend can grey them out.
8. `buckets_a` and `buckets_b` should be ordered: for numeric params use quintile order Q1→Q5; for categorical use alphabetical.

**Extract the grid-building logic** into a private function `_build_interaction_grid(enriched, param_a, dtype_a, param_b, dtype_b)` in the route file. Route handler ≤ 40 lines.

**Auth:** `get_current_user` dependency.

**Performance note:** the enriched-batch cache in `routes_stats.py` is already per-strategy and expires at next bar close. Reuse it for interaction requests too — don't create a second cache. Read how `_get_enriched_batch()` works and call it.

---

## Frontend

### New page: `ui/app/statistics/interactions/page.tsx`

This is a sub-page of statistics. URL: `/statistics/interactions`.

**Page layout:**
1. A back link to `/statistics`
2. A strategy selector (same as the main statistics `ContextBar` — read how that works and reuse the same `useStatsContext` hook)
3. Two dropdowns: "Parameter A" and "Parameter B" — populated from `GET /api/analytics/parameters?strategy=...`
4. The interaction heatmap grid (see component below)
5. A note: "Cells with fewer than 15 signals are greyed out"

Default param_a/param_b selection: on load, if the parent page's summary data is available via URL params or localStorage, pre-select the top two `"confirmed"` params. Otherwise default to the first two params in the list.

**Page must stay ≤ 300 lines.** Extract the heatmap grid as a separate component.

### New component: `ui/components/stats/InteractionHeatmap.tsx`

Props:
```typescript
interface InteractionHeatmapProps {
  data: InteractionResponse | null;
  loading: boolean;
}
```

Renders a grid table where:
- Rows = `buckets_a` labels
- Columns = `buckets_b` labels
- Each cell shows win rate as a percentage + `n` sample count underneath
- Cell background color: use `opacity` of a base color (green for high WR, red for low WR) mapped to win rate. Neutral grey for sparse cells (`win_rate === null`).
- The overall win rate baseline is shown as a reference line or annotation.

Color mapping (inline styles only — dynamic values):
- `win_rate >= overall + 0.10` → strong green tint
- `win_rate >= overall + 0.05` → light green tint
- `win_rate <= overall - 0.10` → strong red tint
- `win_rate <= overall - 0.05` → light red tint
- within ±5pp of overall → neutral
- `win_rate === null` → `bg-surface-2` (greyed out, show "—")

Keep cells compact. This is a data-dense table, not a decorative chart.

### New hook: `ui/lib/useInteraction.ts`

```typescript
export function useInteraction(
  strategy: string,
  paramA: string,
  paramB: string,
  symbol?: string
): { data: InteractionResponse | null; loading: boolean; error: string | null }
```

Fetch on `[strategy, paramA, paramB, symbol]` change. Abort previous request on new call. No polling.

### Add navigation link

In `ui/components/SidebarNav.tsx` (or wherever the statistics sub-navigation lives — check the existing page), add an "Interactions" link pointing to `/statistics/interactions`. It should appear below the main "Statistics" link, indented, similar to how journal sub-pages appear.

---

## Type safety

Add `InteractionCell` and `InteractionResponse` interfaces to `ui/lib/types.ts`.
No `any`. No type assertions.

---

## Tests required

### Backend test: `tests/test_analytics_interaction.py`

```python
def test_interaction_grid_correct_cell_counts():
    # Given 20 signals with known param_a and param_b values
    # Assert correct wins/losses in each cell

def test_interaction_sparse_cell_has_none_win_rate():
    # Cell with total < 15 gets win_rate=None

def test_interaction_invalid_param_returns_422():
    # param_a="nonexistent" → 422

def test_interaction_buckets_ordered_correctly():
    # Numeric params: Q1 before Q5
    # Categorical: alphabetical
```

Run: `python -m pytest tests/test_analytics_interaction.py -v --tb=short`
Full: `python -m pytest tests/ -k "analytics" -v --tb=short`

### Frontend
`cd ui && npx tsc --noEmit` — no errors.

---

## Branch

Work on `feature/analytics-phase4`. Create from `main` (Phase 3 must be merged to main first):
```
git checkout main
git pull
git checkout -b feature/analytics-phase4
```

Three commits: backend endpoint + schema, frontend page + component + hook, navigation wire-in.

When all tests are green and the agent reports done, merge to `main` and delete the branch.
