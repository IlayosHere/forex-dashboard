# Coding Standards

These rules apply to all code in the forex-dashboard project. Every agent and contributor
must follow them. When a rule conflicts with an existing pattern in the codebase, follow
the rule and fix the existing code.

---

## Universal Rules

### File Size Limits

| Layer | Max lines per file | Action when exceeded |
|-------|-------------------|---------------------|
| Python modules | 200 | Extract helpers into a sub-module |
| React components | 250 | Split into composable sub-components |
| React pages | 300 | Extract sections into components |
| Hook files | 150 | One hook per file, extract utilities |
| Type/schema files | 300 | Split by domain (signals, trades, accounts) |
| Config files | 100 | No logic in config files |

Lines are counted excluding blank lines and comments. These are hard limits, not guidelines.

### Function / Component Size Limits

| Type | Max lines | Max parameters |
|------|-----------|----------------|
| Python function | 50 | 6 |
| Python route handler | 40 | 4 (path + query params count as 1 each) |
| React component | 150 (JSX included) | 6 props |
| React hook | 80 | 4 |
| TypeScript utility function | 30 | 4 |

If a function exceeds these limits, extract sub-functions with clear names.

### Naming Conventions

| What | Convention | Example |
|------|-----------|---------|
| Python files | snake_case | `trade_stats.py` |
| Python functions | snake_case | `calculate_lot_size()` |
| Python classes | PascalCase | `TradeModel` |
| Python constants | UPPER_SNAKE | `MAX_SPREAD_PIPS` |
| TypeScript files (components) | PascalCase | `TradeCard.tsx` |
| TypeScript files (utils/hooks) | camelCase | `useSignals.ts` |
| TypeScript functions | camelCase | `fetchSignals()` |
| TypeScript interfaces/types | PascalCase | `TradeResponse` |
| TypeScript constants | UPPER_SNAKE | `BASE_URL` |
| CSS classes | Tailwind utilities only | No custom CSS classes |
| Database columns | snake_case | `candle_time` |
| API endpoints | kebab-case nouns | `/api/trades/stats` |

---

## Python Standards (Backend)

### Import Organization (PEP 8 groups, blank line between each)

```python
from __future__ import annotations          # 1. Future imports

import os                                    # 2. Standard library
from datetime import datetime, timezone

from fastapi import APIRouter, Depends       # 3. Third-party
from sqlalchemy import select

from shared.calculator import pip_size       # 4. Project-local
from api.schemas import TradeResponse
```

Alphabetize within each group. Never use wildcard imports (`from x import *`).

### Type Hints

- **Required** on all function signatures (parameters + return type)
- Use `X | None` instead of `Optional[X]`
- Use `Annotated[type, metadata]` for FastAPI dependencies
- Use `Mapped[type]` for all SQLAlchemy columns (no legacy `Column()`)

```python
# Good
def get_trade(trade_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:

# Bad
def get_trade(trade_id, db):
```

### Docstrings

- **Required** on: route handlers, public functions, classes, modules
- **Not required** on: private helpers (`_prefix`), obvious one-liners
- Style: concise one-liner or Google/NumPy style for complex functions

```python
# Route handler - one-liner is fine
@router.get("/trades/{trade_id}")
def get_trade(...) -> dict:
    """Fetch a single trade by ID, return 404 if not found."""

# Complex function - use structured docstring
def calculate_lot_size(symbol: str, entry: float, sl: float, ...) -> dict:
    """Calculate lot size and risk metrics for a trade.

    Parameters
    ----------
    symbol : str
        Currency pair, e.g. "EURUSD"
    entry : float
        Entry price

    Returns
    -------
    dict with keys: lot_size, risk_usd, pip_value
    """
```

### Error Handling

- Route handlers: use `HTTPException` with appropriate status codes
- Add `logging.getLogger(__name__)` to every API module
- Log warnings for client errors (4xx), log exceptions for server errors (5xx)
- Never catch bare `Exception` in route handlers — let FastAPI handle unexpected errors
- Bare `Exception` is acceptable only at top-level event loops (runner, scanner)

```python
import logging
logger = logging.getLogger(__name__)

@router.get("/trades/{trade_id}")
def get_trade(trade_id: str, db: ...) -> dict:
    """Fetch a single trade by ID."""
    trade = db.get(TradeModel, trade_id)
    if trade is None:
        logger.warning("Trade not found: %s", trade_id)
        raise HTTPException(status_code=404, detail="Trade not found")
    return _serialize_trade(trade)
```

### No Code Duplication

- Utility functions (pip_size, pip_value_per_lot, formatting) live in `shared/`
- If a helper is used in 2+ files, move it to `shared/`
- Strategy-specific logic stays in `strategies/<slug>/`
- Never copy-paste a function between modules — import it

### SQLAlchemy / Pydantic Patterns

```python
# Models: Mapped[] style only
class TradeModel(Base):
    __tablename__ = "trades"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    strategy: Mapped[str] = mapped_column(String, index=True)

# Schemas: Pydantic v2 with ConfigDict
class TradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    strategy: str
```

### Route File Organization

Each route file follows this structure:
1. Imports
2. `router = APIRouter()` with tags
3. Private helper functions (`_prefix`)
4. Route handlers (CRUD order: list, get, create, update, delete)

If a route file exceeds 200 lines, extract helper logic into a service module
(e.g., `api/services/trade_stats.py`).

---

## TypeScript / React Standards (Frontend)

### Import Organization (4 groups, blank line between each)

```typescript
"use client";                                // 0. Directive (if needed)

import { useState, useEffect } from "react"; // 1. React / Next.js
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button"; // 2. Internal components & UI
import { TradeCard } from "@/components/TradeCard";

import type { Trade } from "@/lib/types";    // 3. Types (use `import type`)
import type { TradeFilters } from "@/lib/types";

import { fetchTrades } from "@/lib/api";     // 4. Utils, hooks, constants
import { useTrades } from "@/lib/useTrades";
```

Always use `import type` for type-only imports. Alphabetize within each group.

### Component Structure

Every component file follows this order:
1. Imports
2. Type/interface definitions (props)
3. Helper functions (pure, outside component)
4. Component function
5. Export

```typescript
// 1. Imports
import { useState } from "react";
import type { Trade } from "@/lib/types";

// 2. Props interface
interface TradeCardProps {
  trade: Trade;
  onClose: (id: string) => void;
}

// 3. Helpers (outside component — no re-creation on render)
function formatPnl(pips: number | null): string {
  if (pips === null) return "—";
  return pips >= 0 ? `+${pips.toFixed(1)}` : pips.toFixed(1);
}

// 4. Component
export function TradeCard({ trade, onClose }: TradeCardProps) {
  // hooks first, then derived state, then handlers, then JSX
  const [expanded, setExpanded] = useState(false);
  const isBuy = trade.direction === "BUY";

  function handleClick() { ... }

  return <div>...</div>;
}
```

### Hooks

- One custom hook per file, named `use<Name>.ts`
- Return a typed object, not a tuple (except for simple boolean toggles)
- Always clean up side effects (intervals, subscriptions, AbortController)
- Use `useCallback` for functions passed to `useEffect` deps

```typescript
export interface UseTradesResult {
  trades: Trade[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useTrades(filters: TradeFilters = {}): UseTradesResult {
  // ...
}
```

### TypeScript Strictness

- **No `any`** — use `unknown` if the type is truly unknown, then narrow it
- **No type assertions** (`as Type`) unless interfacing with untyped third-party code
- Use `Record<string, unknown>` instead of `object` for generic key-value data
- Define explicit interfaces for all API request/response shapes
- Use discriminated unions for status-based types

### Styling Rules

- **Tailwind only** — no inline `style={{}}` except for truly dynamic values
  (computed colors based on runtime data)
- Define project colors in `tailwind.config.ts` `theme.extend.colors`
- Use Tailwind color tokens (`bg-surface`, `text-muted`) instead of hex values
- Acceptable inline styles: dynamic conditional colors only (buy/sell, pnl sign)

```typescript
// Good — Tailwind
<div className="bg-surface border border-border rounded-lg p-4">

// Good — dynamic color must be inline
<span style={{ color: pnl >= 0 ? "#26a69a" : "#ef5350" }}>

// Bad — static color in inline style
<div style={{ backgroundColor: "#1a1a1a" }}>
```

### State Management

- Use `useState` for local component state
- Use custom hooks for data fetching (already established)
- If a component has 6+ `useState` calls, consolidate with `useReducer` or extract sub-components
- No global state library needed at current scale

### Page Component Guidelines

Pages (files in `app/`) are orchestrators. They should:
- Fetch data (via hooks)
- Handle routing and URL params
- Compose child components
- NOT contain business logic or complex JSX

If a page exceeds 300 lines, extract sections into dedicated components.

---

## Folder Structure Rules

### When to Create a New File

- A new React component: if it's reused OR if the parent exceeds 250 lines
- A new Python module: if it represents a distinct concern (service, helper, validator)
- A new hook: when fetch/state logic is used in 2+ components, or exceeds 30 lines inline

### When NOT to Create a New File

- One-off helper functions — keep them as private functions in the same file
- Single-use types — define them in the file that uses them
- Tiny components (< 20 lines) used in only one parent — keep inline

### Directory Structure

```
api/
  routes/        ← one file per resource (trades.py, signals.py)
  services/      ← extracted business logic when route files get large
  models.py      ← all SQLAlchemy models (split when > 300 lines)
  schemas.py     ← all Pydantic schemas (split when > 300 lines)
shared/          ← code used by both API and strategies
strategies/
  <slug>/        ← one directory per strategy, always has scanner.py
ui/
  app/           ← Next.js pages only, minimal logic
  components/    ← reusable components (flat unless > 20 files, then group by domain)
  components/ui/ ← shadcn/ui primitives only
  lib/           ← types, api client, hooks, utilities
```

---

## What NOT to Do

These are common mistakes. Do not introduce them:

1. **No `console.log` in committed code** — use proper error states or remove
2. **No commented-out code** — delete it, git has history
3. **No TODO comments without a plan** — fix it now or create an issue
4. **No magic numbers** — extract to named constants
5. **No nested ternaries** — use early returns or `if/else`
6. **No barrel files** (`index.ts` re-exporting everything) — import directly
7. **No default exports** for components — use named exports
8. **No `useEffect` for derived state** — compute it inline with `useMemo` or directly
9. **No Python `print()` for debugging** — use `logging`
10. **No hardcoded URLs or API paths** — use constants or env vars

---

## Checklist Before Submitting Code

Every agent and contributor should verify:

- [ ] No file exceeds its size limit
- [ ] No function exceeds 50 lines (Python) or 150 lines (React component)
- [ ] All functions have type hints (Python) / typed props (TypeScript)
- [ ] Imports are organized in the correct groups
- [ ] No duplicated utility code — shared logic is in `shared/` or `lib/`
- [ ] Route handlers have docstrings
- [ ] Logging is present in API modules
- [ ] No inline styles for static colors (use Tailwind tokens)
- [ ] No `any` types in TypeScript
- [ ] No `console.log` in committed code
