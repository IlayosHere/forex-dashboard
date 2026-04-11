You are adding a new analytics parameter to the forex dashboard.

## Task

Create a parameter named `$ARGUMENTS` that integrates with the registry at
`analytics/params/`, gets computed on every enrichment run, appears in the univariate
report, and is rendered correctly in the UI.

**Read [analytics/AGENTS.md](../../analytics/AGENTS.md) before writing any code.** It
contains the contract every parameter must satisfy (None-for-graceful-degrade, numpy
scalar casting, strategies scope, etc.) and the helper inventory.

## Before you start — get these facts from the user if they aren't in `$ARGUMENTS`

If the user only gave a name, ask these in a single batch (do not ask one at a time):

1. **What does the parameter measure?** One sentence. This becomes the docstring.
2. **Which strategies?** `*` (all), `fvg-impulse` + `fvg-impulse-5m` (both FVG variants),
   `fvg-impulse-5m` only, or `nova-candle` only.
3. **Does it need candles?** I.e., does it read OHLC data, ATR, volume, or anything
   beyond `signal.signal_metadata` + `signal.*` core fields.
4. **What's its dtype?** `float`, `int`, `str`, or `bool`.
5. **Category for the UI?** `when` / `setup` / `momentum` / `cost` — these are the 4 UI
   buckets defined in `ui/lib/analyticsParamMeta.ts::PARAM_CATEGORIES`.
6. **Unit?** `x` (multiplier) / `pips` / `%` / `candles` / `null` — maps to the ParamMeta
   `unit` field and drives axis labels. `isRatio01: true` if the value is a 0–1 ratio
   shown as a percent.

Do not proceed until you have all six. If the user says "figure it out", make a concrete
proposal and ask for confirmation — don't guess silently.

## Steps

### 1. Pick the target file

Decision rules:

| Scope | File |
|---|---|
| `strategies={"*"}` and metadata-only | `analytics/params/temporal.py` if time-based, else `analytics/params/candle_derived.py` |
| `strategies={"*"}` and `needs_candles=True` | `analytics/params/candle_derived.py` |
| `_FVG_STRATEGIES` (both M15 + M5) or `_FVG_5M_STRATEGIES` | `analytics/params/fvg_impulse.py` |
| `_NOVA_STRATEGIES` | `analytics/params/nova_candle.py` |

Do NOT create a new file unless the target file would exceed the 200-effective-line limit
from `docs/coding-standards.md` after the addition. If it would, split by category (e.g.
`analytics/params/volume.py`) and add an import to keep the existing shared helpers
accessible.

### 2. Write the parameter function

Template — pick the variant that matches your (needs_candles, dtype) combo:

#### Numeric, metadata-only

```python
@register("$ARGUMENTS", dtype="float")
def $ARGUMENTS(signal: Any, _candles: pd.DataFrame | None) -> float | None:
    """<one sentence: what this measures>."""
    meta = getattr(signal, "signal_metadata", {}) or {}
    value = meta.get("some_key")
    if value is None:
        return None
    # ... computation ...
    if denom == 0:
        return None
    return float(result)
```

#### Numeric, candle-dependent

```python
@register("$ARGUMENTS", needs_candles=True, dtype="float")
def $ARGUMENTS(signal: Any, candles: pd.DataFrame | None) -> float | None:
    """<one sentence>."""
    if candles is None:
        return None
    idx = _find_signal_bar(candles, signal)
    if idx is None:
        return None
    atr_pips = _atr_pips_at_bar(candles, signal)  # if you need ATR
    if atr_pips is None or atr_pips == 0:
        return None
    # ... computation ...
    return float(result)
```

#### Categorical (`dtype="str"`)

```python
@register("$ARGUMENTS", dtype="str")
def $ARGUMENTS(signal: Any, _candles: pd.DataFrame | None) -> str | None:
    """<one sentence>."""
    # compute a value...
    if value < LOW_THRESHOLD:
        return "low"
    if value > HIGH_THRESHOLD:
        return "high"
    return "normal"
```

Thresholds MUST be module-level constants, not inline literals, so tuning is a one-line
change: `_$ARGUMENTS_LOW = 0.7` at the top of the file.

#### Boolean (`dtype="bool"`)

```python
@register("$ARGUMENTS", needs_candles=True, dtype="bool")
def $ARGUMENTS(signal: Any, candles: pd.DataFrame | None) -> bool | None:
    """<one sentence>."""
    if candles is None:
        return None
    # ... pandas comparison returns numpy.bool_ — cast explicitly! ...
    return bool(lhs > rhs)
```

**The `bool(...)` cast is non-optional.** `numpy.bool_` crashes Pydantic serialization.
This was a real production bug — see `trend_h1_aligned` in
`analytics/params/candle_derived.py` for the cautionary example.

### 3. Use the canonical helpers

Never reinvent these:

| Need | Use |
|---|---|
| Pip size (JPY vs non-JPY) | `from shared.calculator import pip_size` |
| ATR-14 in pips at signal bar | `_atr_pips_at_bar(candles, signal)` from `candle_derived.py` |
| Full ATR series (memoized) | `cached_atr(candles)` from `analytics.candle_cache` |
| H1 resample (memoized) | `cached_h1(candles)` from `analytics.candle_cache` |
| Signal bar index in DataFrame | `_find_signal_bar(candles, signal)` from `candle_derived.py` |
| Volume at signal bar | `_volume_at_bar(candles, signal)` from `candle_derived.py` |
| Broker timezone | `from shared.market_data import EXCHANGE_TZ` |

**Never call `_compute_atr(df)` directly** — it bypasses the `df.attrs` memoization and
makes the route O(signals × bars) instead of O(bars).

### 4. Return None, never raise

Every branch that could fail — missing metadata key, NaN slice, empty window, division by
zero, out-of-range bar index — must return `None`. The stats layer silently drops `None`
before bucketing. An exception propagates up and makes the entire signal's enrichment
noisy in the logs.

Common guards:
```python
if candles is None: return None
if "column_name" not in candles.columns: return None
if idx is None or idx < lookback: return None
if denom == 0 or pd.isna(value): return None
```

### 5. Add the UI metadata

**Every new parameter requires a matching entry in
[ui/lib/analyticsParamMeta.ts](../../ui/lib/analyticsParamMeta.ts).** Without it the
frontend renders the raw snake_case name with no category, no unit, and no bucket labels.

**IMPORTANT**: Read [ui/AGENTS.md](../../ui/AGENTS.md) before touching any file under
`ui/`. The Next.js version in this project has breaking changes from what's in your
training data. For a plain TypeScript data file like `analyticsParamMeta.ts` this
shouldn't matter (it's not a component), but verify the file's existing import style and
match it.

Template:

```ts
$ARGUMENTS: {
  label: "<Human-Readable Label>",        // Title Case, short
  category: "momentum",                    // when | setup | momentum | cost
  description: "<one sentence — shown in tooltips>",
  unit: "x",                               // x | pips | % | candles | null
  isRatio01: false,                        // true only if value is 0–1 shown as %
  // bucketMap: only for categorical / bool params:
  // bucketMap: { low: "Low", normal: "Normal", high: "High" },
},
```

For `dtype="bool"` params, always include a `bucketMap`:
```ts
bucketMap: { True: "Yes", False: "No" },
```

Add the entry under the matching category section in the file (there are comment headers
like `// ===== Momentum & Context =====`). Preserve alphabetical-ish ordering within a
section if the existing file does.

### 6. Write tests

Test file: `tests/test_<name>_params.py` if you're adding a related group, or extend
`tests/test_analytics_candle_params.py` for single params. Match the existing style
exactly — read one of these files first:

- [tests/test_analytics_candle_params.py](../../tests/test_analytics_candle_params.py) — canonical pattern
- [tests/test_volume_params.py](../../tests/test_volume_params.py) — full coverage example

Minimum required tests per parameter:

1. **Happy path** — correct value with realistic inputs.
2. **Returns None without candles** (if `needs_candles=True`) — `your_param(sig, None) is None`.
3. **Returns None with missing metadata / short history / NaN input** — at least one
   degradation test per `None` branch in the function body.
4. **Dtype correctness** — for `bool` params, assert `type(result) is bool` (catches
   numpy.bool_ leaks). For `str`, assert membership in the expected bucket set.

Test scaffolding you can copy from `tests/test_analytics_candle_params.py`:

```python
def _make_candles(n: int = 50, base_price: float = 1.08) -> pd.DataFrame:
    idx = pd.date_range("2025-03-10 00:00", periods=n, freq="15min", tz="UTC")
    return pd.DataFrame({
        "open":  [base_price + i * 0.0001 for i in range(n)],
        "high":  [base_price + i * 0.0001 + 0.0010 for i in range(n)],
        "low":   [base_price + i * 0.0001 - 0.0005 for i in range(n)],
        "close": [base_price + i * 0.0001 + 0.0003 for i in range(n)],
    }, index=idx)

def _signal(**kw: Any) -> MagicMock:
    sig = MagicMock()
    sig.candle_time = kw.get("candle_time") or datetime(2025, 3, 10, 6, 0, tzinfo=timezone.utc)
    sig.symbol = kw.get("symbol", "EURUSD")
    sig.direction = kw.get("direction", "BUY")
    sig.risk_pips = kw.get("risk_pips", 10.0)
    sig.spread_pips = kw.get("spread_pips", 0.5)
    sig.signal_metadata = kw.get("metadata") or {}
    return sig
```

### 7. Run the tests

```
cd /c/GIT-PROJECT/forex-dashboard
python -m pytest tests/test_<your_file>.py -v --tb=short
```

Fix any failures. Before declaring done, also run the broader analytics test suite to
catch regressions in adjacent params:

```
python -m pytest tests/test_analytics_candle_params.py tests/test_analytics_enrichment.py tests/test_analytics_stats.py tests/test_enrichment_tf.py tests/test_analytics_routes_tf.py -v --tb=short
```

All should pass. If a pre-existing test fails, it's not your parameter's problem — check
`git stash` on a baseline to confirm it's pre-existing before chasing it.

### 8. Report back

Tell the user:

1. **Name, category, dtype, strategies scope, needs_candles** — the registration facts.
2. **Where it lives** — which file, which helper functions it uses.
3. **Test count** — how many tests you wrote and that they pass.
4. **UI entry added** — confirm the `ui/lib/analyticsParamMeta.ts` update.
5. **Variance risk** — if the parameter might produce a degenerate distribution (one
   quintile holding 95% of values), flag it so the user knows it may show `level="none"`
   until more data accrues.
6. **Effective on next page load** — remind the user that params are on-the-fly, so
   opening the analytics page immediately surfaces the new column. No migration, no
   backfill.

## Do NOT

- Reinvent `pip_size`, `_compute_atr`, `_find_signal_bar`, or any other helper that's
  already in the inventory. Grep before writing new.
- Add a new parameter without writing the UI metadata entry. The frontend becomes ugly
  and your param will show as `my_thing_bar` in the table.
- Raise exceptions from the param function. Return `None`.
- Forget the `bool(...)` cast on pandas comparisons in `dtype="bool"` params.
- Hardcode a strategy slug inside the param body (`if signal.strategy == "fvg-impulse"`).
  Use the `strategies=` parameter on the decorator instead.
- Store results in a database column. Params are recomputed every request on purpose.
- Add the parameter to `docs/analytics-parameter-refinement.md` — that doc is the design
  archive, not a live index. The registry in `analytics/params/` is the source of truth.
- Create a new test file for a single parameter if a matching file already exists —
  extend the existing file instead.
