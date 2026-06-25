import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

import { useMarketHolidays } from "@/lib/useMarketHolidays";
import type { MarketClosure } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  fetchMarketHolidays: vi.fn(),
}));

import { fetchMarketHolidays } from "@/lib/api";

afterEach(() => {
  vi.restoreAllMocks();
});

function makeClosure(overrides: Partial<MarketClosure> = {}): MarketClosure {
  return {
    id: "cl-1",
    date: "2026-06-19",
    label: "NQ — Juneteenth National Independence Day",
    closure_type: "thin_volume",
    early_close_et: null,
    note: "NQ trades normal hours, but volume is typically thin.",
    ...overrides,
  };
}

const THIN_VOLUME = makeClosure();
const FULL_CLOSE = makeClosure({ id: "cl-2", closure_type: "full_close", date: "2026-12-25" });

describe("useMarketHolidays", () => {
  beforeEach(() => {
    vi.mocked(fetchMarketHolidays).mockResolvedValue([THIN_VOLUME, FULL_CLOSE]);
  });

  it("returns all closures returned by the API", async () => {
    const { result } = renderHook(() => useMarketHolidays({ week: "current" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.closures).toHaveLength(2);
  });

  it("loading starts true and becomes false after fetch", async () => {
    const { result } = renderHook(() => useMarketHolidays({ week: "current" }));
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
  });

  it("error is null on successful fetch", async () => {
    const { result } = renderHook(() => useMarketHolidays({ week: "current" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeNull();
  });
});

describe("useMarketHolidays — error handling", () => {
  it("sets error message when fetch throws", async () => {
    vi.mocked(fetchMarketHolidays).mockRejectedValue(new Error("Network failure"));
    const { result } = renderHook(() => useMarketHolidays({ week: "current" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Network failure");
  });

  it("closures remain empty on error", async () => {
    vi.mocked(fetchMarketHolidays).mockRejectedValue(new Error("Network failure"));
    const { result } = renderHook(() => useMarketHolidays({ week: "current" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.closures).toHaveLength(0);
  });
});
