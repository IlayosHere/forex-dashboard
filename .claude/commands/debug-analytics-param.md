You are diagnosing a misbehaving analytics parameter in the forex dashboard.

## Task

The user has a parameter named `$ARGUMENTS` that is producing unexpected output — it
returns `None` too often, shows `level="none"` in the univariate report, returns the
same value for every signal, throws an error, or just looks wrong. Find the cause and
propose (or apply) a fix.

**Read [analytics/AGENTS.md](../../analytics/AGENTS.md) first.** It documents the
parameter contract, helper inventory, 9-level classifier, and common mistakes. Most
debugging questions are answered there.

## Diagnostic flowchart — work through these in order

Do not skip steps. Each builds on the previous.

### Step 1 — Locate the parameter

```
grep -rn "\"$ARGUMENTS\"" analytics/params/
```

You should see exactly one `@register("$ARGUMENTS", ...)` line. Read the function body
AND its decorator arguments. Note:

- `strategies=` — is it scoped correctly? A param registered for `_NOVA_STRATEGIES` will
  not run on fvg-impulse signals.
- `needs_candles=` — if `True`, the param is skipped when the cache returns `None` for
  the symbol (tvDatafeed down, unknown pair).
- `dtype=` — must match the Python type of every non-None return value.

If you can't find it in `analytics/params/`, the parameter isn't registered. Check that
the containing module is imported from `analytics/params/__init__.py` (autoload by
import) or that `analytics.params` is imported somewhere at app startup.

### Step 2 — Classify the symptom

Ask the user which of these matches, or read the report output if they pasted it:

| Symptom | Likely cause | Jump to |
|---|---|---|
| Every signal's value is `None` | Param returns `None` on a guard that's always true | Step 3 |
| Some signals have values, others are `None` | Graceful degradation on specific data shapes | Step 4 |
| All signals have the same non-`None` value | Degenerate computation or upstream data issue | Step 5 |
| Report shows `level="none"` but values look fine | Low variance or insufficient buckets | Step 6 |
| HTTP 500 on `/api/analytics/enriched` or `/univariate/$ARGUMENTS` | Serialization crash, usually numpy scalar | Step 7 |
| Value is wrong but the code looks right | Wrong timeframe candles — the M5 bug | Step 8 |

### Step 3 — "Every signal returns None"

Read the function body top-to-bottom. List every `return None` branch. For each, ask:

1. **Is the guard condition always `True` for this dataset?** Common culprits:
   - `if candles is None: return None` — is the route wiring the cache at all? Check
     `analytics/routes.py` and `analytics/routes_stats.py` — they MUST call
     `enrich_with_candles(signals)`, not plain `enrich_batch(signals)`.
   - `if "volume" not in candles.columns: return None` — the user's symbol may not have
     volume. Run the experiment in `scratch/volume_check.py` to verify.
   - `if idx is None: return None` — `_find_signal_bar` couldn't locate the signal's
     `candle_time` in the candle DataFrame. This happens when the signal is older than
     the cache window (480 M15 bars ≈ 5 days). Historical signals from weeks ago will
     silently hit this.
   - `if idx < lookback: return None` — the signal bar is too close to the start of the
     fetched window. Common for the first few hours of the cache's range.
   - `if metadata.get("key") is None: return None` — the metadata key isn't actually
     populated. Check `strategies/*/scanner.py::_to_signal` — does it persist this key?

2. **To verify which guard fires**, add a `logger.debug` temporarily (remove before
   committing):
   ```python
   logger.debug("$ARGUMENTS debug: candles=%s idx=%s meta_keys=%s",
                candles is None, idx, list(meta.keys()))
   ```
   Hit the endpoint once, grep the logs, remove the line.

3. **If the guard is firing on old signals only**, the fix is usually to widen
   `_BAR_COUNTS` in `analytics/candle_cache.py`. Don't do this silently — coordinate with
   the user because it multiplies tvDatafeed fetch cost.

### Step 4 — "Some signals are None, others aren't"

This is graceful degradation working as designed for missing data, or a real data
quality problem. Pick one signal with `None` and one with a value, and compare their:

- `signal.signal_metadata` dicts — is the `None` one missing a key?
- `signal.candle_time` — is it very old (pre-cache window)?
- `signal.symbol` — does the `None` symbol have volume / spread data / H1 resample?

If the pattern is "JPY pairs return None, majors don't" or similar, you likely have a
pip-size bug — use `pip_size(symbol)` from `shared/calculator.py`, never hardcode
`0.0001`.

If the pattern is "signals older than N days return None", widen `_BAR_COUNTS`.

### Step 5 — "All values are identical"

Three common causes:

1. **You're computing something at the end of the DataFrame instead of at the signal
   bar.** Bug example:
   ```python
   # WRONG — uses the last bar of the fetched window for every signal
   return float(atr_series.iloc[-1])
   ```
   Every signal in the same cache run gets the same value — the latest ATR. Fix:
   ```python
   idx = _find_signal_bar(candles, signal)
   return float(atr_series.iloc[idx])
   ```
   `trend_h1_aligned` and `volatility_percentile` in `analytics/params/candle_derived.py`
   currently have this exact pattern (known deferred bug) — check if your param copied
   from them.

2. **Thresholds are outside the observed data range.** If your categorical bucketing is
   `low < 0.001 / normal / high > 100.0`, everything ends up in `normal`. Inspect the raw
   distribution before finalizing thresholds.

3. **Metadata key is constant across the dataset.** E.g., if you read `fvg_direction`
   and the strategy already splits by direction, every FVG signal has the same value.
   Kill the param — it has no information.

### Step 6 — "Values look fine but level='none'"

The CI classifier in `analytics/stats/classification.py` assigns `level="none"` when no
bucket's win rate deviates from the overall win rate by ≥ 5 percentage points with
statistical confidence (Bonferroni-corrected).

This can be a legitimate verdict ("this parameter doesn't predict outcomes") OR a
symptom of one of these:

1. **Not enough data.** Each quintile needs enough signals for the two-proportion CI to
   resolve. Check `total_signals` in the report. Under ~100 resolved signals per
   strategy, `level="none"` is the default state for almost everything. Wait for more
   data before concluding.

2. **Min-bucket filter is dropping buckets.** Open
   `analytics/stats/filters.py::filter_min_bucket` — the `MIN_BUCKET_SIZE` constant
   drops buckets smaller than that threshold. A numeric param with 5 quintiles on 100
   signals means each bucket has ~20 entries; if `MIN_BUCKET_SIZE` is higher, you lose
   buckets and the CI collapses.

3. **Quintile split degeneracy.** If 95% of values sit in one narrow range,
   `quintile_split` collapses four of the five quintiles into a single bucket and you
   get a 1-bucket or 2-bucket split. Inspect the raw distribution — print
   `pd.Series([s["params"]["$ARGUMENTS"] for s in enriched]).describe()`.

4. **Parameter is genuinely uncorrelated with outcomes.** The valid verdict. Don't
   delete it yet — low-sample-size `none` can become `hint` or `real` with more data.
   Keep the param, revisit in a month.

### Step 7 — "HTTP 500 on the analytics endpoint"

Check the FastAPI/uvicorn logs for the Pydantic serialization error. **9 out of 10
times** it's:

```
PydanticSerializationError: Unable to serialize unknown type: <class 'numpy.bool_'>
```

or

```
PydanticSerializationError: Unable to serialize unknown type: <class 'numpy.int64'>
```

Fix: cast explicitly in the param function body.

```python
# WRONG — returns numpy.bool_
return ema.iloc[-1] > ema.iloc[-4]

# RIGHT
return bool(ema.iloc[-1] > ema.iloc[-4])
```

```python
# WRONG — returns numpy.int64
return (window <= bar_vol).sum() / len(window) * 100

# RIGHT
return int((window <= bar_vol).sum()) / len(window) * 100
# or equivalently: float(((window <= bar_vol).sum()) / len(window) * 100)
```

Look at every return statement in the function. If it touches `.iloc`, `.sum()`,
`.mean()`, `.values`, or any pandas comparison, wrap the final result in `float(...)`,
`int(...)`, or `bool(...)`.

Other 500 causes: exception inside the param body (check `logger.exception` lines from
`resolve_all_params` in `analytics/registry.py`).

### Step 8 — "Value is wrong but the code looks right"

Almost always a timeframe mismatch. Steps:

1. **Which strategy is the signal from?** `fvg-impulse-5m` signals should be computed
   against M5 candles. Check `analytics/candle_cache.py::STRATEGY_INTERVALS` — is the
   strategy registered? If missing, it falls back to M15 silently.

2. **Run the invariant test** to confirm scanner ↔ registry agreement:
   ```
   python -m pytest tests/test_enrichment_tf.py::test_strategy_intervals_match_scanner_declarations -v
   ```

3. **Inspect the actual candle DataFrame** handed to your param. Add a temporary log:
   ```python
   logger.info("$ARGUMENTS got %d bars at cadence %s", len(candles),
               candles.index[1] - candles.index[0])
   ```
   You should see the expected cadence (5min for M5 strategies, 15min for M15). If
   you see M15 cadence on an M5 strategy, `STRATEGY_INTERVALS` is wrong.

4. **Check the memoized helpers.** If the param uses `cached_atr(candles)` and you see
   stale values, it's because `df.attrs` memoization is scoped to the DataFrame
   instance, not globally. Different requests get fresh DataFrames (per-request cache),
   so stale values between requests aren't a bug — only within-request.

## Useful one-liners

Quickly inspect a param's distribution over the live database:

```python
# python -c "..."
from api.db import SessionLocal
from analytics.enrichment import enrich_with_candles, fetch_resolved

db = SessionLocal()
signals = fetch_resolved(db, strategy="fvg-impulse", limit=500)
enriched = enrich_with_candles(signals)
values = [s["params"].get("$ARGUMENTS") for s in enriched]
print(f"total={len(values)} non_none={sum(1 for v in values if v is not None)}")
import pandas as pd
print(pd.Series([v for v in values if v is not None]).describe())
db.close()
```

Inspect the full univariate report for the param:

```
curl -s "http://localhost:8000/api/analytics/univariate/$ARGUMENTS?strategy=fvg-impulse" | python -m json.tool
```

(Only works if the backend is running locally.)

## Reporting back

Tell the user:

1. **Root cause in one sentence** — e.g., "every signal returns None because
   `_find_signal_bar` cannot locate the signal's `candle_time` in the fetched 480-bar
   window; the signals are older than the cache range."
2. **The exact fix** — file path, line numbers, before/after. If it's a data issue
   rather than a code issue, say so and stop (don't invent a code fix for data).
3. **Whether you applied the fix or are waiting for approval** — some fixes (like
   bumping `_BAR_COUNTS`) have cost implications the user should decide on.
4. **Tests** — if you changed code, confirm the affected tests still pass.
5. **Whether the fix propagates automatically** — remind the user that params are
   on-the-fly, so the next page load reflects the correction. No backfill needed.

## Do NOT

- Silently widen `_BAR_COUNTS` or change thresholds without telling the user.
- Add a `try/except: pass` around the param body to "fix" a crash. Find the root cause.
- Delete a param that shows `level="none"` unless you've confirmed it's genuinely
  uncorrelated with outcomes AND you have enough data for that verdict to stick.
- Rewrite the parameter's formula to produce "nicer" values when the raw computation is
  correct. The stats layer is robust to wide distributions; don't pre-scale.
- Invent a backfill script. There is no backfill. Params are on-the-fly.
