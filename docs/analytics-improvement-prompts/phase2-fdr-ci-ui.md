# Phase 2 — FDR Correction + CI Bars + Sample Size UI

## What you are doing

You are improving the statistical quality and UI of the analytics summary. Three changes:

1. **Backend** — add Benjamini-Hochberg FDR correction across all parameters in the summary response, so each param is marked `"confirmed"`, `"exploratory"`, or `"insufficient_data"`.
2. **Backend** — add `n_signals` per bucket to the univariate response so the UI can show sample size.
3. **Frontend** — update `ui/components/ParamRankingTable.tsx` to show CI bars, sample size badges, and the confirmed/exploratory distinction.

No new parameters. No database changes. No new pages.

---

## Mandatory first reads

1. `docs/coding-standards.md` — all code must comply with size limits, naming, type hints.
2. `analytics/stats/report.py` — this is where `build_summary()` lives. You will modify it.
3. `analytics/stats/classification.py` — the 9-level CI classifier. Read to understand `best_bucket_analysis()`.
4. `analytics/schemas.py` — Pydantic response models. You will add a field to `CorrelationItem` and `SummaryResponse`.
5. `analytics/routes_stats.py` — the route that calls `build_summary()`. Read but you likely won't change it.
6. `ui/components/ParamRankingTable.tsx` — the component you will update.
7. `ui/components/SignificancePill.tsx` — already exists, understand its API.
8. `ui/components/SampleSizeNotice.tsx` — already exists, understand its API.
9. `ui/lib/analyticsParamMeta.ts` — understand the metadata structure.

---

## Backend changes

### Change 1: Add FDR status to `build_summary()` in `analytics/stats/report.py`

After `_rank_params()` produces its list of rows, apply Benjamini-Hochberg FDR correction across all rows that have a non-None `level`.

**Algorithm (Benjamini-Hochberg):**
```
Given m hypothesis tests with p-values p_1 ≤ p_2 ≤ ... ≤ p_m, at FDR level q=0.10:
For i from m down to 1:
    if p_i ≤ (i/m) * q:
        reject all hypotheses 1..i
        break
```

For the forex dashboard, use the existing `p_value` field already in each row (from `chi_p_value` or `correlation_p_value` depending on dtype). Use `q = 0.10` (10% FDR).

Assign `fdr_status` to each row:
- `"confirmed"` — this param's p-value survived BH at q=0.10 AND `level` is not `"none"`
- `"exploratory"` — did not survive BH but `level` is not `"none"` (passed within-param Bonferroni only)
- `"insufficient_data"` — `level` is `"none"` or p-value is None

Add `fdr_status: str` to the returned dict for each param in `top_correlations`.

**Important constraint:** The FDR computation must be extracted as a private function `_apply_fdr(rows, q=0.10)` in `report.py`. Max 50 lines per function.

### Change 2: Add `fdr_status` field to `CorrelationItem` in `analytics/schemas.py`

```python
fdr_status: str = "insufficient_data"
```

### Change 3: Expose `n` per bucket in `BucketWinRateResponse`

`BucketWinRateResponse` already has `total: int` — that's the n. No schema change needed. Verify the field is populated correctly in `win_rate_by_bucket()` in `analytics/stats/univariate.py`. If it's already there, no change needed.

---

## Frontend changes

Read the current `ui/components/ParamRankingTable.tsx` fully before making any changes.

### Change 1: FDR status badge per row

Each row in the table should show a small badge next to the param name:
- `"confirmed"` → green pill `"Confirmed"`
- `"exploratory"` → yellow/amber pill `"Exploratory"`
- `"insufficient_data"` → grey, no pill (just omit the badge)

Use the existing `SignificancePill` component if it fits; otherwise add a small inline badge using Tailwind only. No new component file unless the logic exceeds 20 lines.

### Change 2: CI bar instead of a single number

Currently the table shows a win-rate delta point estimate. Add a visual CI bar:
- A thin horizontal bar showing the range `[ci_lo, ci_hi]` anchored at `delta=0`
- Width of the bar maps to the CI width; the bar position shows whether CI is entirely positive, negative, or straddles zero
- Use inline styles only for the dynamic width/position calculations (Tailwind can't do runtime arithmetic)
- Keep it compact — this is a table row, not a chart

### Change 3: Sample size badge on the summary

The `SummaryResponse` already has `total_resolved`. Display it with a colour-coded badge at the top of the table:
- ≥ 100 signals → green
- 50–99 → amber/yellow
- < 50 → red, add tooltip: "Results below 50 signals are exploratory only"

Also show the per-bucket `n` in the univariate detail view if it's already accessible through the existing API response (check `BucketWinRateResponse.total`).

---

## Type safety rules (mandatory)

- No `any` types in TypeScript. Use the existing `CorrelationItem` type from `ui/lib/types.ts` (or wherever it's defined — check first).
- If you need to extend the type, add `fdr_status: "confirmed" | "exploratory" | "insufficient_data"` to it.
- All new props interfaces must be explicit.

---

## Tests required

### Backend test
Create `tests/test_analytics_fdr.py`:

```python
def test_fdr_marks_confirmed_when_significant():
    # Build a list of rows where one has a very small p-value
    # Assert that row gets fdr_status="confirmed"

def test_fdr_marks_exploratory_when_borderline():
    # p-value passes Bonferroni but not BH
    # Assert fdr_status="exploratory"

def test_fdr_marks_insufficient_when_none_level():
    # level="none" rows always get "insufficient_data"

def test_fdr_empty_input():
    # Empty list returns empty list, no crash
```

Run: `python -m pytest tests/test_analytics_fdr.py -v --tb=short`
Also run: `python -m pytest tests/ -k "analytics" -v --tb=short` — no regressions.

### Frontend
No automated test required for the visual changes. Verify manually that:
- The table renders without TypeScript errors (`cd ui && npx tsc --noEmit`)
- The badges appear correctly for each FDR status

---

## Branch

Work on branch `feature/analytics-phase2`. Create from `main` (Phase 1 must be merged to main first):
```
git checkout main
git pull
git checkout -b feature/analytics-phase2
```

Commit separately: one commit for backend changes, one for frontend changes.

When all tests are green and the agent reports done, merge to `main` and delete the branch before starting Phase 3.
