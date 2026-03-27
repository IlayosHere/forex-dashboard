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

### 4. Verify the interface

After creating the files, check:
- `strategies/$ARGUMENTS/scanner.py` exports a `scan()` function
- `scan()` returns `list[Signal]` (can be empty)
- `Signal` is imported from `shared.signal`
- The strategy slug `$ARGUMENTS` matches the entry added in `ui/lib/strategies.ts`

### 5. Report back

Tell the user:
- What files were created
- What they need to implement in `scan_symbol()`
- That the runner will pick it up automatically on next start (no runner changes needed)
- That the UI page `/strategy/$ARGUMENTS` is already available once the strategy is in `strategies.ts`
