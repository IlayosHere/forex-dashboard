# Analytics — Agent Context

This file is auto-loaded when you work in [analytics/](.). Read it before touching anything
in this directory. It captures the architecture, invariants, and non-obvious gotchas that
would otherwise take you hours of code-reading to reconstruct.

If you want to ADD a new analytics parameter, use `/add-analytics-param <name>` instead of
reinventing the workflow.
If you're DEBUGGING a param that returns `None` or shows `level="none"`, use
`/debug-analytics-param <name>`.

**Model routing:** All analytics work is execution — use `sonnet`. Switch with `/model sonnet`
before touching this package. Only escalate to `opus` if you need to redesign the parameter
registry architecture or the CI classifier levels.

---

## What this package does

Takes resolved signals (TP_HIT / SL_HIT) and runs a registry of "parameter" functions
against each one. Each parameter is a small pure function that extracts a feature from
the signal (session hour, FVG width, ATR at the signal bar, etc.). The stats layer then
buckets each parameter's values and asks "does any bucket's win rate deviate from the
overall win rate in a statistically and economically meaningful way?"

Output: a univariate report per parameter + a summary ranked by the CI classifier.

The trader uses this to decide which signals to take and which to skip. That's the whole
product of this directory.

---

## File layout

```
analytics/
  registry.py              @register decorator, resolve_all_params()
  types.py                 Session, PairCategory enums, ParamDef dataclass
  enrichment.py            fetch_resolved(), enrich_batch(), enrich_with_candles()
  candle_cache.py          CandleCache + STRATEGY_INTERVALS + cached_atr / cached_h1
  routes.py                GET /api/analytics/enriched
  routes_stats.py          GET /api/analytics/univariate/{name}, /api/analytics/summary
  schemas.py               Pydantic response models
  stats/
    classification.py      9-level CI classifier — the "verdict" on each param
    univariate.py          win_rate_by_bucket, two_proportion_ci, chi_squared_test
    report.py              build_univariate_report(), build_summary()
    filters.py             category_split, quintile_split, filter_min_bucket
  params/                  ← most new work lands here
    temporal.py            session_label, day_of_week
    spread.py              spread_risk_ratio, pair_category
    candle_derived.py      atr_14, trend_h1_aligned, volatility_percentile,
                           risk_pips_atr, relative_volume, volume_percentile,
                           volume_regime  — plus shared helpers _find_signal_bar,
                           _atr_pips_at_bar, _volume_at_bar
    fvg_impulse.py         FVG-specific params (shared between M15 and M5 variants)
    nova_candle.py         Nova-specific params + spread_tier
```

---

## The Parameter function contract

Every parameter is a function decorated with `@register` in `analytics/registry.py`.
This is the entire contract — internalize it.

```python
@register(
    name: str,                            # unique identifier, becomes the dict key
    strategies: frozenset[str] = {"*"},   # strategy slugs, or "*" for all
    needs_candles: bool = False,          # if True, engine passes OHLC DataFrame
    dtype: str = "float",                 # "float" | "int" | "str" | "bool"
)
def my_param(signal: Any, candles: pd.DataFrame | None) -> float | None:
    ...
```

**Invariants that MUST hold:**

1. **Always `(signal, candles)` — two positional arguments.** Even if you don't need
   `candles`, you must accept it. If `needs_candles=False`, the engine passes `None`.
2. **Return `None` for graceful degradation. NEVER raise.** Missing metadata, insufficient
   history, NaN inputs, division-by-zero guard — all return `None`. The stats layer
   silently drops `None` values before bucketing. An exception crashes the entire
   enrichment for that signal; `resolve_all_params` has a try/except around each call,
   but it's sloppy to rely on it.
3. **Return a Python scalar matching the declared `dtype`.**
   - `dtype="float"` → Python `float` or `None`
   - `dtype="int"` → Python `int` or `None`
   - `dtype="str"` → Python `str` (any value) or `None`
   - `dtype="bool"` → Python `bool` (NOT `numpy.bool_`!) or `None`
4. **Cast numpy scalars explicitly.** Pandas comparison operators return `numpy.bool_`,
   which Pydantic refuses to serialize into JSON. This is the single most common bug.
   `bool(series.iloc[-1] > series.iloc[-4])`, not `series.iloc[-1] > series.iloc[-4]`.
   Same for `float(x)` when `x` is `numpy.float64` and you're doing arithmetic that
   could hit a pandas result. See the `trend_h1_aligned` fix in
   [params/candle_derived.py](params/candle_derived.py) for the cautionary example.
5. **Categorical params: ≤ 10 distinct values.** More buckets than that and the CI
   classifier's Bonferroni correction eats the signal. See `Z_CRITICAL` in
   [stats/classification.py](stats/classification.py).
6. **Numeric params need variance.** If 95% of signals fall into one quintile, the param
   is dead. Flag this as variance risk in the docstring when the risk is real.
7. **No outcome leakage.** The value must be computable at the moment the signal fires,
   not after. Never look forward in the candle DataFrame past `signal.candle_time`.
8. **Strategies scope:** `frozenset({"fvg-impulse", "fvg-impulse-5m"})` for FVG-only,
   `frozenset({"nova-candle"})` for Nova-only, or `{"*"}` (the default — omit the argument)
   for cross-strategy params that apply everywhere.

---

## How timeframe routing works — the STRATEGY_INTERVALS registry

**This is the single most important architectural invariant in the analytics package.**

When a param has `needs_candles=True`, the engine passes it an OHLC DataFrame. The DataFrame
comes from the `CandleCache` which fetches candles at the **strategy's native timeframe**,
not a hardcoded default. The mapping lives in exactly one place:

```python
# analytics/candle_cache.py
STRATEGY_INTERVALS: dict[str, Interval] = {
    "fvg-impulse":    Interval.in_15_minute,
    "fvg-impulse-5m": Interval.in_5_minute,
    "nova-candle":    Interval.in_15_minute,
}
```

**Adding a new strategy at a new timeframe is a one-line change.** Add the entry, done.
Params automatically get the right timeframe. The cache keys every entry by
`(symbol, interval)` so M5 and M15 coexist for the same symbol without collision.

**Do not hardcode `Interval.in_15_minute` (or any other TF) anywhere outside this
registry.** The `/add-strategy` slash command enforces this; the test
`test_strategy_intervals_match_scanner_declarations` in
[tests/test_enrichment_tf.py](../tests/test_enrichment_tf.py) guards against drift.

### There was a bug here

Before 2026-04, `CandleCache` always fetched M15 regardless of strategy. Every
`needs_candles=True` param for `fvg-impulse-5m` was silently computed against
**M15 bars containing the M5 signal**, not the M5 signal bar. Stored historical values
for that strategy are wrong. This is fixed and the next enrichment run will overwrite
them (params are on-the-fly; see below).

---

## Params are computed on-the-fly, never persisted

`SignalModel` stores raw signal fields. **It does not store any `params` column.**
Every call to the analytics endpoints recomputes params from scratch. There is no
"backfill" or "re-enrichment" command — the next hit to
`/api/analytics/enriched`, `/api/analytics/univariate/{name}`, or `/api/analytics/summary`
produces fresh values.

**Implication:** when you change a parameter's formula, tune a threshold, or fix a bug,
the correction is automatic on the next page load. No migration, no script, no flag.

**Implication 2:** when you ADD a new parameter, every historical resolved signal
instantly participates in the statistics. Do not wait for new data to validate.

---

## Available helpers — reuse these, do NOT reinvent

### `analytics/params/candle_derived.py`

| Helper | What it does | Use when |
|---|---|---|
| `_find_signal_bar(candles, signal)` | Returns the integer index of the signal's bar in the candle DataFrame (ffill). `None` if out of range. | Your param needs the bar position. |
| `_atr_pips_at_bar(candles, signal)` | Returns ATR-14 in pips at the signal bar. Uses memoized ATR. | Any param that normalizes against volatility. |
| `_volume_at_bar(candles, signal)` | Returns tick count at the signal bar, or `None` if the column is missing or NaN. | Volume-based params. |

### `analytics/candle_cache.py`

| Helper | What it does | Use when |
|---|---|---|
| `cached_atr(df, period=14)` | Memoized ATR series on `df.attrs`. Shared across all params that see the same DataFrame. | Param needs the ATR series, not a single bar value. |
| `cached_h1(df)` | Memoized H1 OHLC resample on `df.attrs`. | Param needs an H1 view. |
| `interval_for_strategy(strategy)` | Returns the `Interval` enum for a strategy slug, with M15 fallback. | Rarely directly — the cache handles it. |

**Do NOT call `_compute_atr` directly from params.** It bypasses memoization and
recomputes the full ATR series per-signal. That's the exact inefficiency the cleanup pass
fixed. Always go through `cached_atr` or `_atr_pips_at_bar`.

**Do NOT call `candles.resample("1h").agg(...)` inline.** Use `cached_h1(candles)`.

### `shared/calculator.py`

| Helper | What it does |
|---|---|
| `pip_size(symbol)` | Returns 0.01 for JPY pairs, 0.0001 otherwise. Use for all pip math. Never reinvent the JPY check. |
| `pip_value_per_lot(symbol, price)` | USD pip value per standard lot. Rarely needed from params. |

### `shared/market_data.py`

| Helper | What it does |
|---|---|
| `EXCHANGE_TZ` | `ZoneInfo("Asia/Jerusalem")` — broker timezone constant. Re-exported here to avoid `analytics/` reaching into `strategies/`. |
| `get_candles(symbol, interval, count)` | TF-blind candle fetcher. The cache uses this; params should never call it directly. |

---

## The 9-level CI classifier — reading the output

[stats/classification.py](stats/classification.py) assigns every parameter a `level` based on
its best-differentiating bucket vs the rest of the data. The ladder (from strongest to weakest):

| Level | Meaning |
|---|---|
| `strong_positive` | CI entirely above +5pp — this bucket is a real, strong edge |
| `strong_negative` | CI entirely below -5pp — this bucket is a real, strong anti-edge |
| `real_positive` | CI entirely positive but doesn't clear +5pp — modest real effect |
| `real_negative` | CI entirely negative but doesn't clear -5pp |
| `suggestive_positive` | CI straddles 0 but observed delta ≥ 10pp — directional hint at larger sample |
| `suggestive_negative` | Same, negative direction |
| `hint_positive` | CI straddles 0, delta ≥ 5pp — weakest positive signal |
| `hint_negative` | Same, negative direction |
| `none` | delta < 5pp or no bucket differs meaningfully — param does nothing |

A `level="none"` verdict is not a bug; it's a valid conclusion: "this parameter doesn't
predict outcomes in the data we have." See `/debug-analytics-param` for when to care.

The "5pp" threshold is `ECONOMIC_THRESHOLD = 0.05` in
[stats/classification.py](stats/classification.py) — win-rate percentage points, NOT a
p-value. The two numerically coincide but are semantically unrelated. Don't confuse them.

---

## The enrichment pipeline — what actually runs on a request

1. Route handler calls `fetch_resolved(db, strategy=..., symbol=..., limit=...)` →
   SQL for resolved (TP_HIT or SL_HIT) signals.
2. Route handler calls `enrich_with_candles(signals)` →
   creates a per-request `CandleCache`, warms it with the unique `(symbol, strategy)`
   pairs, then calls `enrich_batch(signals, candle_cache=cache)`.
3. For each signal, `enrich_batch` calls `resolve_all_params(signal, signal.strategy,
   candles=cache.get(signal.symbol, signal.strategy))`.
4. `resolve_all_params` iterates registered params for that strategy. For each:
   - Skip if `needs_candles=True` and `candles is None` (symbol fetch failed gracefully).
   - Call the param function; catch any exception, log, store `None`.
5. Returns a list of `{signal fields..., "params": {name: value, ...}}` dicts.
6. Stats layer buckets the values and builds the report / summary.

**Graceful degradation:** if tvDatafeed is down or rate-limited for one symbol, that
symbol's signals get `candles=None`, every candle-dependent param returns `None`, and the
response still ships. Metadata-only params (session, day-of-week, spread ratios)
always work.

---

## Common mistakes (the cautionary list)

1. **`numpy.bool_` in a `dtype="bool"` param.** Pandas comparisons return numpy scalars.
   Pydantic refuses to serialize them. Always wrap: `bool(a > b)`.
2. **Calling `_compute_atr(df)` from a param.** Bypasses the per-DataFrame memoization.
   Use `cached_atr(df)` or `_atr_pips_at_bar(df, signal)`.
3. **Raising from a param.** Never. Return `None`. Missing metadata keys → `None`.
   Division by zero → `None`. Empty slice → `None`. Always guard, never throw.
4. **Adding a param without updating [ui/lib/analyticsParamMeta.ts](../ui/lib/analyticsParamMeta.ts).**
   The frontend will render your param as the raw snake_case name without a category,
   unit, or bucket labels. Every new param requires a matching entry.
5. **Hardcoding `Interval.in_15_minute` anywhere outside `STRATEGY_INTERVALS`.** Breaks
   the adaptive design. Use the registry.
6. **Using `datetime.fromisoformat` on metadata without tz-normalizing.** The stored ISO
   string may or may not have `+00:00`. Normalize with
   `if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)`.
7. **Forgetting that `fvg-impulse` and `fvg-impulse-5m` share the same param file.** Scope
   with `strategies=_FVG_STRATEGIES` (shared) or `strategies=_FVG_5M_STRATEGIES` (M5-only).
   Both frozensets live at the top of [params/fvg_impulse.py](params/fvg_impulse.py).
8. **Reading `signal.signal_metadata` without a default.** Use `getattr(signal, "signal_metadata", {}) or {}`.
   It can be `None` for signals from older schemas.
9. **Volume params without the `"volume" in candles.columns` check.** Not every pair/TF
   returns volume. See `_volume_at_bar` for the canonical pattern.
10. **Bar-count assumptions.** The M15 cache fetches 480 bars (~5 days), M5 fetches 1440
    bars. If your param needs more history, bump `_BAR_COUNTS` in
    [candle_cache.py](candle_cache.py) — don't silently return `None` for lack of bars.

---

## Testing conventions

Tests live in [tests/test_analytics_*.py](../tests/). Match the existing style exactly:

- `_make_candles(n, base_price)` — deterministic OHLC DataFrame, M15 default,
  UTC-tz-aware index. For other timeframes, pass `freq="5min"` via a parameterized helper.
- `_signal(**kwargs)` — `MagicMock` with `candle_time`, `symbol`, `direction`, `risk_pips`,
  `spread_pips`, `signal_metadata`.
- One test per happy path, one per `None` path (missing metadata, no candles, insufficient
  history, NaN input). At minimum four tests per new param.
- Float assertions: `pytest.approx(expected, abs=0.01)`.
- Run with `python -m pytest tests/test_my_param.py -v --tb=short`.

See [tests/test_analytics_candle_params.py](../tests/test_analytics_candle_params.py) and
[tests/test_volume_params.py](../tests/test_volume_params.py) for canonical examples.

---

## When you are stuck

1. **Param returns `None` too often** → `/debug-analytics-param <name>`.
2. **Param serializes but shows `level="none"`** → check variance. Quintile split may be
   collapsing everything into one bucket. Read `filter_min_bucket` in
   [stats/filters.py](stats/filters.py) — the `MIN_BUCKET_SIZE` constant is probably
   dropping your buckets.
3. **Param works in isolation but the route returns 500** → almost certainly a numpy
   scalar leak. Pydantic error will mention the type. Fix with explicit Python `bool()` /
   `float()` / `int()` cast.
4. **New strategy's params operate on wrong-TF candles** → you forgot to add the entry
   to `STRATEGY_INTERVALS`. `/add-strategy` has a step for this now.
5. **ATR computes are slow on large reports** → someone called `_compute_atr` directly
   instead of `cached_atr`. Grep for it.

---

## Do not

- Re-debate the 9-level CI classifier thresholds — they're in `docs/adr/` (forthcoming)
  and in `stats/classification.py`'s module docstring.
- Add a `params` column to `SignalModel`. Params are on-the-fly. If you want caching,
  it belongs in the per-request `CandleCache`, not in the database.
- Introduce a parameter whose computation is non-deterministic (time-of-day, random,
  external API call). Params must be pure functions of `(signal, candles)`.
- Move helpers out of `params/candle_derived.py` into a separate file "for cleanliness".
  The current layout is a deliberate choice — `candle_derived.py` is the shared-helper
  module, other param files import from it.
