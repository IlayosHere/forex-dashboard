import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

import { useCalendar } from "@/lib/useCalendar";
import type { CalendarEvent } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  fetchCalendar: vi.fn(),
}));

import { fetchCalendar } from "@/lib/api";

afterEach(() => {
  vi.restoreAllMocks();
});

function makeEvent(overrides: Partial<CalendarEvent> = {}): CalendarEvent {
  return {
    id: "ev-1",
    name: "CPI m/m",
    currency: "USD",
    datetime_utc: "2026-04-04T12:30:00Z",
    datetime_et: "2026-04-04T08:30:00Z",
    impact: "High",
    promoted: false,
    previous: null,
    forecast: null,
    actual: null,
    beat_miss: "pending",
    session_bucket: "cash_session",
    ...overrides,
  };
}

const USD_EVENT = makeEvent({ id: "usd-1", currency: "USD", name: "Non-Farm Payrolls" });
const CNY_PMI_EVENT = makeEvent({ id: "cny-1", currency: "CNY", name: "China PMI" });
const CNY_OTHER_EVENT = makeEvent({ id: "cny-2", currency: "CNY", name: "Trade Balance" });
const JPY_BOJ_EVENT = makeEvent({ id: "jpy-1", currency: "JPY", name: "BOJ Rate Decision" });
const JPY_OTHER_EVENT = makeEvent({ id: "jpy-2", currency: "JPY", name: "Tokyo CPI" });
const EUR_EVENT = makeEvent({ id: "eur-1", currency: "EUR", name: "ECB Rate Decision" });
const GBP_EVENT = makeEvent({ id: "gbp-1", currency: "GBP", name: "UK CPI" });

const ALL_EVENTS = [
  USD_EVENT,
  CNY_PMI_EVENT,
  CNY_OTHER_EVENT,
  JPY_BOJ_EVENT,
  JPY_OTHER_EVENT,
  EUR_EVENT,
  GBP_EVENT,
];

describe("useCalendar — forex context", () => {
  beforeEach(() => {
    vi.mocked(fetchCalendar).mockResolvedValue(ALL_EVENTS);
  });

  it("returns all events when context is forex", async () => {
    const { result } = renderHook(() => useCalendar({ week: "current", context: "forex" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.events).toHaveLength(ALL_EVENTS.length);
  });

  it("loading starts true and becomes false after fetch", async () => {
    const { result } = renderHook(() => useCalendar({ week: "current", context: "forex" }));
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
  });

  it("error is null on successful fetch", async () => {
    const { result } = renderHook(() => useCalendar({ week: "current", context: "forex" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBeNull();
  });
});

describe("useCalendar — mnq context filtering", () => {
  beforeEach(() => {
    vi.mocked(fetchCalendar).mockResolvedValue(ALL_EVENTS);
  });

  it("includes USD events", async () => {
    const { result } = renderHook(() => useCalendar({ week: "current", context: "mnq" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.events.some((e) => e.id === "usd-1")).toBe(true);
  });

  it("includes CNY events named 'China PMI'", async () => {
    const { result } = renderHook(() => useCalendar({ week: "current", context: "mnq" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.events.some((e) => e.id === "cny-1")).toBe(true);
  });

  it("excludes CNY events NOT named 'China PMI'", async () => {
    const { result } = renderHook(() => useCalendar({ week: "current", context: "mnq" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.events.some((e) => e.id === "cny-2")).toBe(false);
  });

  it("includes JPY events named 'BOJ ...'", async () => {
    const { result } = renderHook(() => useCalendar({ week: "current", context: "mnq" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.events.some((e) => e.id === "jpy-1")).toBe(true);
  });

  it("excludes JPY events NOT named 'BOJ ...'", async () => {
    const { result } = renderHook(() => useCalendar({ week: "current", context: "mnq" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.events.some((e) => e.id === "jpy-2")).toBe(false);
  });

  it("excludes EUR events", async () => {
    const { result } = renderHook(() => useCalendar({ week: "current", context: "mnq" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.events.some((e) => e.id === "eur-1")).toBe(false);
  });

  it("excludes GBP events", async () => {
    const { result } = renderHook(() => useCalendar({ week: "current", context: "mnq" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.events.some((e) => e.id === "gbp-1")).toBe(false);
  });

  it("returns empty array when no events are MNQ-relevant", async () => {
    vi.mocked(fetchCalendar).mockResolvedValue([EUR_EVENT, GBP_EVENT]);
    const { result } = renderHook(() => useCalendar({ week: "current", context: "mnq" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.events).toHaveLength(0);
  });
});

describe("useCalendar — error handling", () => {
  it("sets error message when fetch throws", async () => {
    vi.mocked(fetchCalendar).mockRejectedValue(new Error("Network failure"));
    const { result } = renderHook(() => useCalendar({ week: "current", context: "forex" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Network failure");
  });

  it("sets fallback error string when thrown value is not an Error", async () => {
    vi.mocked(fetchCalendar).mockRejectedValue("bad");
    const { result } = renderHook(() => useCalendar({ week: "current", context: "forex" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Failed to load calendar");
  });

  it("events remain empty on error", async () => {
    vi.mocked(fetchCalendar).mockRejectedValue(new Error("Network failure"));
    const { result } = renderHook(() => useCalendar({ week: "current", context: "forex" }));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.events).toHaveLength(0);
  });
});
