You are helping the user scaffold a new trading strategy for the forex dashboard.

## Task

Create a new strategy package under `strategies/$ARGUMENTS/` with the correct structure and interface so it integrates automatically with the runner, API, and UI.

## Steps

### 1. Create the strategy folder structure

Create these files:
- `strategies/$ARGUMENTS/__init__.py` — empty
- `strategies/$ARGUMENTS/scanner.py` — main interface (see template below)
- `strategies/$ARGUMENTS/calculations.py` — trade parameter calculations (copy and adapt from `strategies/fvg-impulse/calculations.py`)
- `strategies/$ARGUMENTS/config.py` — if the strategy needs its own spread/config overrides; otherwise import from shared

### 2. scanner.py template

```python
"""
strategies/$ARGUMENTS/scanner.py
---------------------------------
[Strategy name] — brief description of the pattern it detects.

Implements the standard scan() interface:
    scan() -> list[Signal]
"""
from __future__ import annotations

from datetime import datetime, timezone
from shared.signal import Signal


STRATEGY_NAME = "$ARGUMENTS"
PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "USDCAD", "AUDUSD", "NZDUSD",
]


def scan() -> list[Signal]:
    """
    Run the strategy scanner across all pairs.
    Called by the runner after each candle close.
    Returns a list of Signal objects (empty list if no signals).
    """
    signals: list[Signal] = []
    for pair in PAIRS:
        result = scan_symbol(pair)
        if result:
            signals.append(result)
    return signals


def scan_symbol(symbol: str) -> Signal | None:
    """
    Scan a single symbol for a signal.
    Return a Signal if one is detected, None otherwise.
    """
    # TODO: implement strategy logic here
    # 1. Fetch candle data (use tvDatafeed like fvg-impulse)
    # 2. Detect pattern
    # 3. Calculate SL/TP
    # 4. Return Signal or None

    return None


def _build_signal(
    symbol: str,
    direction: str,
    candle_time: datetime,
    entry: float,
    sl: float,
    tp: float,
    lot_size: float,
    risk_pips: float,
    spread_pips: float,
    metadata: dict,
) -> Signal:
    """Helper: construct a Signal with all required fields."""
    return Signal(
        strategy=STRATEGY_NAME,
        symbol=symbol,
        direction=direction,
        candle_time=candle_time,
        entry=entry,
        sl=sl,
        tp=tp,
        lot_size=lot_size,
        risk_pips=risk_pips,
        spread_pips=spread_pips,
        metadata=metadata,
    )
```

### 3. Register the strategy in the UI

Add an entry to `ui/lib/strategies.ts`:

```typescript
{ slug: "$ARGUMENTS", label: "[Human readable name]", description: "[One line description]" },
```

### 4. Register the strategy with the analytics TF registry — MANDATORY

**Do not skip this step.** If you skip it, every candle-dependent analytics parameter
will silently compute against the wrong timeframe for this strategy. This was a real
production bug (the "M5 bug") before `STRATEGY_INTERVALS` existed.

In [strategies/$ARGUMENTS/scanner.py](../../strategies/$ARGUMENTS/scanner.py), declare a
module-level constant at the top of the file naming the scanner's native timeframe:

```python
from tvDatafeed import Interval

# Native timeframe for this strategy. Must match STRATEGY_INTERVALS
# in analytics/candle_cache.py — test_strategy_intervals_match_scanners
# enforces this invariant.
_STRATEGY_INTERVAL: Interval = Interval.in_15_minute   # or in_5_minute, in_1_hour, etc.
```

Use `_STRATEGY_INTERVAL` in every `get_candles(...)` call inside the scanner body.
Never hardcode `Interval.in_15_minute` at a call site.

Then add the strategy to the registry in
[analytics/candle_cache.py](../../analytics/candle_cache.py):

```python
STRATEGY_INTERVALS: dict[str, Interval] = {
    "fvg-impulse":    Interval.in_15_minute,
    "fvg-impulse-5m": Interval.in_5_minute,
    "nova-candle":    Interval.in_15_minute,
    "$ARGUMENTS":     Interval.in_15_minute,   # ← add this line
}
```

If the strategy uses a timeframe not already present in `_BAR_COUNTS` (e.g. H1), also add
an entry there so the cache fetches enough bars for HTF resampling:

```python
_BAR_COUNTS: dict[Interval, int] = {
    Interval.in_5_minute:  1440,   # ~5 days
    Interval.in_15_minute:  480,   # ~5 days
    Interval.in_1_hour:     168,   # ~7 days for H1 strategies
}
```

Finally, extend the invariant test in
[tests/test_enrichment_tf.py](../../tests/test_enrichment_tf.py)::
`test_strategy_intervals_match_scanner_declarations` to include the new strategy's
scanner so the registry-scanner agreement is enforced in CI:

```python
from strategies.$ARGUMENTS import scanner as new_scanner

assert (
    STRATEGY_INTERVALS["$ARGUMENTS"] == new_scanner._STRATEGY_INTERVAL
), "STRATEGY_INTERVALS['$ARGUMENTS'] is out of sync with strategies/$ARGUMENTS/scanner.py"
```

Run the test to confirm:

```
cd /c/GIT-PROJECT/forex-dashboard
python -m pytest tests/test_enrichment_tf.py -v --tb=short
```

### 5. Verify the interface

After creating the files, check:
- `strategies/$ARGUMENTS/scanner.py` exports a `scan()` function
- `scan()` returns `list[Signal]` (can be empty)
- `Signal` is imported from `shared.signal`
- The strategy slug `$ARGUMENTS` matches the entry added in `ui/lib/strategies.ts`
- `_STRATEGY_INTERVAL` is declared in the scanner module and used at every `get_candles` call
- `STRATEGY_INTERVALS["$ARGUMENTS"]` in `analytics/candle_cache.py` matches the scanner's declared interval
- `test_strategy_intervals_match_scanner_declarations` passes

### 6. Report back

Tell the user:
- What files were created or modified
- What they need to implement in `scan_symbol()`
- That the runner will pick it up automatically on next start (no runner changes needed)
- That the UI page `/strategy/$ARGUMENTS` is already available once the strategy is in `strategies.ts`
- That analytics for the new strategy will automatically compute against the correct
  timeframe because of the `STRATEGY_INTERVALS` entry — no param code changes needed
