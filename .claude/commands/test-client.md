You are writing frontend tests for the forex dashboard.

## Context

- **Test runner**: Vitest 4 with jsdom, React Testing Library 16, @testing-library/jest-dom
- **Config**: `ui/vitest.config.ts` — jsdom env, globals enabled, setup in `ui/tests/setup.ts`
- **Run tests**: `cd ui && npx vitest run` (all) or `npx vitest run tests/path/to/file.test.ts` (single)
- **Existing tests**: `ui/tests/` — check what already exists before writing duplicates
- **Strategy doc**: Read `docs/frontend-testing-strategy.md` for priorities, patterns, and rules

## What to do

$ARGUMENTS determines the scope:

- **No arguments or "all"**: Run the full test suite, report results, and identify files that still need tests based on the priority tiers in the strategy doc.
- **A file path** (e.g., `lib/useCalculator.ts`): Write tests for that specific source file. Place the test in `ui/tests/` mirroring the source path (e.g., `ui/tests/lib/useCalculator.test.ts`).
- **"missing"**: Analyze which MUST TEST and SHOULD TEST files from the strategy doc don't have test files yet, list them, and ask which to write.
- **"fix"**: Run the test suite, and for any failing tests, read the source file and the test file, diagnose the failure, and fix the test (or the source if the test reveals a real bug).

## Steps for writing tests

1. **Read the source file** — understand every function, branch, and edge case
2. **Read the strategy doc** — check the priority tier and "what to cover" column for this file
3. **Check for existing tests** — don't duplicate. Extend if the file exists, create if not
4. **Read existing test files** for style reference — match the patterns in `ui/tests/lib/api.test.ts` and `ui/tests/components/StatsBar.test.tsx`
5. **Write tests** following these rules:
   - Import from `vitest` (`describe`, `it`, `expect`, `vi`, `beforeEach`, `afterEach`)
   - Import `render`, `screen`, `fireEvent` from `@testing-library/react` for component tests
   - Import `renderHook`, `waitFor`, `act` from `@testing-library/react` for hook tests
   - Use `vi.stubGlobal("fetch", ...)` for API mocking (not MSW)
   - Use `vi.useFakeTimers()` for debounce/interval testing
   - Mock `next/navigation` at the top of files that need router:
     ```ts
     vi.mock("next/navigation", () => ({
       useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
       useSearchParams: () => new URLSearchParams(""),
       usePathname: () => "/",
     }));
     ```
   - Test behavior, not implementation details
   - One clear behavior per `it()` block
   - Always clean up: `afterEach(() => { vi.restoreAllMocks(); })`
6. **Run the tests** — `cd ui && npx vitest run` — and fix any failures
7. **Report results** — show pass/fail count and what was covered

## Test patterns by file type

### Pure functions (strategies.ts, formatting helpers)
```ts
describe("functionName", () => {
  it("handles normal case", () => { expect(fn(input)).toBe(expected); });
  it("handles edge case", () => { expect(fn(edge)).toBe(expected); });
});
```

### Hooks (useCalculator, useTrades, useSignals)
```ts
import { renderHook, waitFor, act } from "@testing-library/react";

describe("useMyHook", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true, json: () => Promise.resolve(mockData),
    }));
  });
  afterEach(() => { vi.restoreAllMocks(); });

  it("fetches data on mount", async () => {
    const { result } = renderHook(() => useMyHook());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(expected);
  });
});
```

### Components with interactions (TradeForm, TagInput)
```ts
import { render, screen, fireEvent } from "@testing-library/react";

// Mock next/navigation if component uses useRouter
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(""),
}));

describe("MyComponent", () => {
  it("validates required fields on submit", () => {
    render(<MyComponent {...props} />);
    fireEvent.click(screen.getByText("Save"));
    expect(screen.getByText("Error message")).toBeInTheDocument();
  });
});
```

### Display components (StatsBar, TradeCard)
```ts
describe("MyDisplay", () => {
  it("renders data correctly", () => {
    render(<MyDisplay data={mockData} />);
    expect(screen.getByText("expected text")).toBeInTheDocument();
  });

  it("shows placeholder when data is null", () => {
    render(<MyDisplay data={null} />);
    expect(screen.getByText("\u2014")).toBeInTheDocument();
  });
});
```

## Do NOT

- Write snapshot tests
- Assert on CSS class names (assert on visible text or behavior instead)
- Test shadcn/ui primitives (Button, Input, Sheet)
- Test type definitions
- Add tests for things already well-covered
- Use `@testing-library/react-hooks` (it's deprecated; use `renderHook` from `@testing-library/react`)
