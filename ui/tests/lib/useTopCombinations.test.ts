import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

import { useTopCombinations } from "@/lib/useTopCombinations";

import type { TopCombinationsResponse } from "@/lib/types";

const BASE_URL = "http://localhost:8000";

function makeResponse(overrides: Partial<TopCombinationsResponse> = {}): TopCombinationsResponse {
  return {
    strategy: "fvg-impulse",
    symbol: null,
    total_signals: 100,
    overall_win_rate: 0.5,
    confirmed_param_count: 4,
    pairs_scanned: 6,
    cells_evaluated: 24,
    items: [],
    reason: null,
    ...overrides,
  };
}

function mockFetchOk(data: unknown) {
  return vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(data),
  });
}

beforeEach(() => {
  vi.stubGlobal("localStorage", {
    getItem: vi.fn().mockReturnValue("fake-token"),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useTopCombinations", () => {
  it("starts with loading=false and data=null when strategy is empty", () => {
    vi.stubGlobal("fetch", mockFetchOk(makeResponse()));
    const { result } = renderHook(() => useTopCombinations(""));
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("does not fetch when strategy is empty string", () => {
    const mockFetch = mockFetchOk(makeResponse());
    vi.stubGlobal("fetch", mockFetch);
    renderHook(() => useTopCombinations(""));
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("sets loading=true while fetching", async () => {
    let resolve!: (v: unknown) => void;
    const pending = new Promise((res) => { resolve = res; });
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(pending));
    const { result } = renderHook(() => useTopCombinations("fvg-impulse"));
    expect(result.current.loading).toBe(true);
    resolve({ ok: true, json: () => Promise.resolve(makeResponse()) });
  });

  it("populates data on successful fetch", async () => {
    const response = makeResponse({ confirmed_param_count: 8, pairs_scanned: 28 });
    vi.stubGlobal("fetch", mockFetchOk(response));
    const { result } = renderHook(() => useTopCombinations("fvg-impulse"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(response);
    expect(result.current.error).toBeNull();
  });

  it("calls the correct endpoint URL with strategy param", async () => {
    const mockFetch = mockFetchOk(makeResponse());
    vi.stubGlobal("fetch", mockFetch);
    renderHook(() => useTopCombinations("fvg-impulse"));
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain(`${BASE_URL}/api/analytics/top-combinations`);
    expect(url).toContain("strategy=fvg-impulse");
  });

  it("appends symbol to the URL when provided", async () => {
    const mockFetch = mockFetchOk(makeResponse());
    vi.stubGlobal("fetch", mockFetch);
    renderHook(() => useTopCombinations("fvg-impulse", "EURUSD"));
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).toContain("symbol=EURUSD");
  });

  it("does not append symbol when not provided", async () => {
    const mockFetch = mockFetchOk(makeResponse());
    vi.stubGlobal("fetch", mockFetch);
    renderHook(() => useTopCombinations("fvg-impulse"));
    await waitFor(() => expect(mockFetch).toHaveBeenCalled());
    const url = mockFetch.mock.calls[0][0] as string;
    expect(url).not.toContain("symbol=");
  });

  it("sets error on non-ok response", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    const { result } = renderHook(() => useTopCombinations("fvg-impulse"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toContain("500");
    expect(result.current.data).toBeNull();
  });

  it("sets error on network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network down")));
    const { result } = renderHook(() => useTopCombinations("fvg-impulse"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Network down");
  });

  it("clears error on re-fetch after error", async () => {
    const failFetch = vi.fn().mockResolvedValue({ ok: false, status: 503 });
    vi.stubGlobal("fetch", failFetch);
    const { result, rerender } = renderHook(
      ({ strategy }: { strategy: string }) => useTopCombinations(strategy),
      { initialProps: { strategy: "fvg-impulse" } },
    );
    await waitFor(() => expect(result.current.error).not.toBeNull());

    vi.stubGlobal("fetch", mockFetchOk(makeResponse()));
    rerender({ strategy: "nova-candle" });
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeNull();
  });
});
