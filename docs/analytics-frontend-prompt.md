# Signal Analytics Frontend — Build Prompt

Paste this at the start of a new Claude Code conversation to build the analytics UI.

---

## What Already Exists

### Backend (fully built and tested — do NOT modify)

Four API endpoints in `analytics/` module, mounted at `/api/analytics/`:

```
GET /api/analytics/parameters?strategy=fvg-impulse
GET /api/analytics/enriched?strategy=&symbol=&limit=50
GET /api/analytics/univariate/{param_name}?strategy=fvg-impulse
GET /api/analytics/summary?strategy=fvg-impulse
```

All require JWT auth (same as all other endpoints).

### Response Shapes

**GET /api/analytics/summary?strategy=fvg-impulse**
```typescript
{
  strategy: string;
  total_resolved: number;
  win_rate_overall: number;        // 0.0 - 1.0
  params_analyzed: number;
  top_correlations: {
    param_name: string;
    correlation: number;
    p_value: number;
    significant: boolean;          // p < 0.05
  }[];
}
```

**GET /api/analytics/univariate/{param_name}?strategy=fvg-impulse**
```typescript
{
  param_name: string;
  dtype: "categorical" | "numeric";
  strategy: string;
  total_signals: number;
  buckets: {
    bucket_label: string;          // "LONDON" or "Q1 (0.02-0.05)"
    wins: number;
    losses: number;
    total: number;
    win_rate: number;              // 0.0 - 1.0
    ci_lower: number;              // Wilson CI lower bound
    ci_upper: number;              // Wilson CI upper bound
  }[];
  chi_squared: number | null;
  chi_p_value: number | null;
  correlation: number | null;
  correlation_p_value: number | null;
}
```

**GET /api/analytics/parameters?strategy=fvg-impulse**
```typescript
{
  items: {
    name: string;
    dtype: "float" | "str" | "int" | "bool";
    strategies: string[];          // ["*"] for shared, ["fvg-impulse", "fvg-impulse-5m"] for specific
    needs_candles: boolean;
  }[];
  total: number;
}
```

### Strategies Available

From `ui/lib/strategies.ts` — read this file for the current registry. The three strategies are:
- `fvg-impulse` — FVG Impulse M15
- `fvg-impulse-5m` — FVG Impulse 5M
- `nova-candle` — Nova Candle M15

### Existing Frontend Patterns

Read these files to match patterns exactly:
- `ui/app/layout.tsx` — root layout, nav, dark mode
- `ui/app/journal/page.tsx` — page with filters + data table + stats (closest pattern to what we're building)
- `ui/components/StatsBar.tsx` — stat display pattern
- `ui/components/TradeFilters.tsx` — filter component pattern
- `ui/lib/api.ts` — typed fetch wrappers (follow this pattern for analytics fetchers)
- `ui/lib/types.ts` — TypeScript interfaces
- `ui/lib/useSignals.ts` — data fetching hook pattern with polling
- `ui/app/globals.css` — design tokens (@theme block)

### Tech Stack (decided, do not change)
- Next.js 14 App Router, TypeScript strict mode
- shadcn/ui + Tailwind, dark mode only
- No external chart libraries — use pure Tailwind for bar charts

---

## What to Build

### Page Structure

```
/analytics                        → Strategy overview + readiness
/analytics/[strategy]             → Deep dive for one strategy
```

### Page 1: `/analytics` — Overview

A table showing each strategy with:
- Strategy name (from strategies.ts registry)
- Resolved signal count
- Overall win rate (as percentage)
- Sample size readiness indicator (progress toward 150 threshold)
- Top significant parameter (or "Need 150+ signals" if insufficient)

One `/api/analytics/summary` call per strategy.

Click a row → navigate to `/analytics/[strategy]`.

### Page 2: `/analytics/[strategy]` — Deep Dive

**Section A: Header Stats**
- Strategy name, total resolved signals, overall win rate
- Sample size notice if below 150

**Section B: Parameter Ranking Table**
- All parameters sorted by p-value ascending (most significant first)
- Columns: Parameter name, Type (categorical/numeric), p-value, Significant (checkmark if p < 0.05)
- Populated from `/api/analytics/summary` top_correlations
- Click a row → show its bucket breakdown in Section C

**Section C: Win Rate Bucket Chart (for selected parameter)**
- Fetched from `/api/analytics/univariate/{param_name}`
- Horizontal bar chart, one bar per bucket
- Bar length = win rate (0% to 100%)
- Confidence interval shown as whisker lines or semi-transparent extended bar
- Color coding: green-ish for above overall win rate, red-ish for below
- 50% baseline reference line
- Each bar labeled: bucket name, win rate %, count (n=XX)
- Below the chart: significance test result (chi² p-value or correlation + p-value)

### Pure Tailwind Bar Chart (no chart library)

The bucket chart is horizontal bars built with Tailwind:
```tsx
// Each bucket is a row:
<div className="flex items-center gap-3">
  <span className="w-32 text-sm truncate">{label}</span>
  <div className="flex-1 h-6 bg-zinc-800 rounded relative">
    <div className="h-full rounded bg-emerald-600/80" style={{ width: `${winRate * 100}%` }} />
    {/* CI whiskers as absolute-positioned thin bars */}
  </div>
  <span className="w-20 text-sm text-right">{pct}% (n={total})</span>
</div>
```

---

## File Structure to Create

```
ui/
  app/analytics/
    page.tsx                       ← overview page
    [strategy]/
      page.tsx                     ← deep dive page
  components/
    StrategyReadinessTable.tsx      ← overview table with readiness indicators
    ParamRankingTable.tsx           ← sortable significance table
    WinRateBuckets.tsx              ← horizontal bar chart with CIs
    SampleSizeNotice.tsx            ← "87/150 signals" progress bar
  lib/
    analyticsApi.ts                 ← typed fetch wrappers for 4 endpoints
    useAnalyticsSummary.ts          ← hook: fetch summary per strategy
    useUnivariateReport.ts          ← hook: fetch single param bucket data
```

Plus: add "Analytics" link to the navigation in layout.tsx.

---

## UX Decisions (already made, do not re-debate)

1. **No auto-polling** — analytics data changes slowly (when signals resolve over hours/days). Use a manual "Refresh" button, not 30s polling.
2. **No annotations on SignalCard** — the engine analyzes populations, not individual signals. Don't add per-signal scores.
3. **No candle-dependent params toggle yet** — current API returns null for candle params (they need TradingView fetch). Just skip null params in the display. Phase 2 adds opt-in candle analysis.
4. **No heatmaps yet** — Phase 3, needs multivariate analysis with 300+ signals.
5. **Results are data, not decisions** — show numbers, confidence intervals, significance. Don't add "RECOMMENDED" or "SKIP" labels. The trader interprets.
6. **Strategies below 150 signals** — show data anyway (wide CIs tell the story), but display a clear "Low sample size" notice.
7. **Dark mode only** — matches the rest of the dashboard.

---

## Agent Workflow

Use the UI/UX Problem Protocol from CLAUDE.md:

1. **Before writing any component**, spawn both in parallel:
   - `UI Designer` — visual design, color, spacing, dark-mode component patterns
   - `UX Architect` — information hierarchy, interaction model, data density

2. Give them: the design tokens from `ui/app/globals.css`, the existing component patterns, the data shapes above, and the wireframe descriptions from this doc.

3. Synthesize their recommendations, then implement with:
   - `Rapid Prototyper` — for page scaffolding and component wiring
   - `Frontend Developer` — for polish, accessibility, responsive behavior

4. After building: run `/test-client` to write and run frontend tests.
5. After tests pass: run `/simplify` to review for quality.

---

## Key Constraints

- **MANDATORY**: Read `docs/coding-standards.md` before writing any code
- React components: 250 lines max per file
- Hooks: 150 lines max, one hook per file
- TypeScript: no `any`, use `import type` for type-only imports
- All shadcn components live in `ui/components/ui/` — check what's already installed
- Follow import organization: React/Next → internal components → types → utils/hooks
- Add Analytics types to `ui/lib/types.ts` (don't create a separate types file)
