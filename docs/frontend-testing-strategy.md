# Frontend Testing Strategy

## Stack

| Layer | Tool | Status |
|-------|------|--------|
| Unit + Component | Vitest 4 + React Testing Library 16 | Installed |
| DOM matchers | @testing-library/jest-dom | Installed |
| User interactions | @testing-library/user-event | **Needs install** |
| API mocking (unit) | `vi.stubGlobal("fetch")` | In use |
| API mocking (integration) | MSW 2 | Installed, not configured |
| E2E | Playwright | **Future** |

## File Structure

Tests live in `ui/tests/`, mirroring the source tree:

```
ui/tests/
  setup.ts                          # jest-dom matchers
  mocks/
    next-navigation.ts              # shared mock for useRouter/useSearchParams/usePathname
  lib/
    api.test.ts                     # fetch wrapper URL construction + errors
    strategies.test.ts              # pure function registry lookups
    utils.test.ts                   # cn() utility
    useCalculator.test.ts           # debounce, localStorage, NaN guards, signal reset
    useTrades.test.ts               # cancelled trade hiding, polling
    useSignals.test.ts              # fetch + poll pattern
    useTradeStats.test.ts           # basic fetch hook
  components/
    StarRating.test.tsx             # click toggle, hover
    StatusBadge.test.tsx            # status/outcome rendering
    StatsBar.test.tsx               # stat cards, formatting
    TradeForm.test.tsx              # validation, account-strategy cross-filter
    TradeInfoPanel.test.tsx         # edit/display toggle, save/cancel, external sync
    TradeCard.test.tsx              # P&L formatting, direction styling
    TradeResultPanel.test.tsx       # formatDuration, pnlColor
    TagInput.test.tsx               # add/remove/dedup, keyboard, suggestions
    TradeCloseActions.test.tsx      # disabled states, outcome callbacks
    Calculator.test.tsx             # null vs populated display
  pages/
    trade-detail-reducer.test.ts    # editableReducer unit test
    new-trade-utils.test.ts         # pipSize, toLocalDatetime
```

## Priority Tiers

### MUST TEST (business-critical)

| File | Type | What to cover |
|------|------|---------------|
| `lib/useCalculator.ts` | Hook | pipSize, toPips, debounce timing, localStorage read/write, NaN inputs, signal reset |
| `lib/api.ts` | Unit | URL construction for all 12 functions, error throwing |
| `components/TradeForm.tsx` | Integration | 8-field validation, account-strategy cross-filter, submit payload |
| `components/TradeInfoPanel.tsx` | Integration | Edit/display toggle, inline validation, save/cancel, external sync |
| `lib/strategies.ts` | Unit | getInstrumentType fallback, getUnitLabel, getSizeLabel |
| `journal/[id]/page.tsx` reducer | Unit | editableReducer LOAD and SET_FIELD actions |

### SHOULD TEST (moderate risk)

| File | Type | What to cover |
|------|------|---------------|
| `lib/useTrades.ts` | Hook | Cancelled trade hiding when no status filter |
| `components/StatsBar.tsx` | Render | Formatting helpers, null stats, loading state |
| `components/TradeCard.tsx` | Render | P&L sign/dollar formatting, direction styling |
| `components/TradeResultPanel.tsx` | Unit | formatDuration (running vs closed) |
| `components/TagInput.tsx` | Integration | Add/remove/dedup, Enter/Escape, suggestion mousedown |
| `components/StarRating.tsx` | Integration | Click toggle, hover preview |
| `components/TradeCloseActions.tsx` | Integration | Disabled states, outcome callbacks |

### NICE TO HAVE

TradeFilters, SignalFilters, AccountSheet, AccountStatsStrip, SignalCard, Calculator display, MetadataPanel, useSignals, useTradeStats, useAccounts.

### SKIP

- `lib/types.ts` (type-only)
- shadcn/ui primitives (Button, Input, Sheet, etc.)
- Page-level orchestration (better as E2E)
- Snapshot tests (fragile, low value)
- CSS class name assertions (test behavior, not styling)

## Patterns

### Mocking next/navigation

```ts
// tests/mocks/next-navigation.ts
import { vi } from "vitest";

export const mockPush = vi.fn();
export const mockReplace = vi.fn();
export const mockBack = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush, replace: mockReplace, back: mockBack }),
  useSearchParams: () => new URLSearchParams(""),
  usePathname: () => "/",
}));
```

### Testing hooks with renderHook

```ts
import { renderHook, waitFor, act } from "@testing-library/react";

const { result } = renderHook(() => useMyHook(args));
await waitFor(() => expect(result.current.loading).toBe(false));
```

### Debounce testing

```ts
vi.useFakeTimers();
// trigger state change
await act(async () => { vi.advanceTimersByTime(300); });
// assert API was called
vi.useRealTimers();
```

### API mocking

```ts
vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve(data),
}));
```

## Rules

1. **Test behavior, not implementation** -- assert on what the user sees, not internal state
2. **Prefer `userEvent` over `fireEvent`** for realistic interaction simulation
3. **No snapshot tests** -- they break on every UI change and provide false confidence
4. **One assertion focus per test** -- each `it()` tests one behavior
5. **Mock at the boundary** -- mock `fetch`, not internal functions
6. **Pure functions first** -- they are trivially testable and highest ROI per line of test code
