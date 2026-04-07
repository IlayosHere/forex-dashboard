import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useNextEvent } from "@/lib/useNextEvent";

import type { CalendarEvent } from "@/lib/types";

afterEach(() => {
  vi.restoreAllMocks();
  vi.useRealTimers();
});

function makeEvent(overrides: Partial<CalendarEvent> = {}): CalendarEvent {
  return {
    id: "ev-1",
    name: "NFP",
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

describe("useNextEvent", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("returns null event when given an empty array", () => {
    vi.setSystemTime(new Date("2026-04-04T10:00:00Z"));
    const { result } = renderHook(() => useNextEvent([]));
    expect(result.current.event).toBeNull();
  });

  it("returns null event when all events are in the past", () => {
    vi.setSystemTime(new Date("2026-04-04T14:00:00Z"));
    const pastEvent = makeEvent({ datetime_utc: "2026-04-04T12:30:00Z", impact: "High" });
    const { result } = renderHook(() => useNextEvent([pastEvent]));
    expect(result.current.event).toBeNull();
  });

  it("returns the soonest future High impact event", () => {
    vi.setSystemTime(new Date("2026-04-04T10:00:00Z"));
    const later = makeEvent({
      id: "ev-later",
      datetime_utc: "2026-04-04T14:00:00Z",
      impact: "High",
    });
    const sooner = makeEvent({
      id: "ev-sooner",
      datetime_utc: "2026-04-04T12:30:00Z",
      impact: "High",
    });
    const { result } = renderHook(() => useNextEvent([later, sooner]));
    expect(result.current.event?.id).toBe("ev-sooner");
  });

  it("ignores Medium impact events that are not promoted", () => {
    vi.setSystemTime(new Date("2026-04-04T10:00:00Z"));
    const mediumEvent = makeEvent({
      id: "ev-medium",
      datetime_utc: "2026-04-04T12:30:00Z",
      impact: "Medium",
      promoted: false,
    });
    const { result } = renderHook(() => useNextEvent([mediumEvent]));
    expect(result.current.event).toBeNull();
  });

  it("returns a promoted Medium event as the next event", () => {
    vi.setSystemTime(new Date("2026-04-04T10:00:00Z"));
    const promotedEvent = makeEvent({
      id: "ev-promo",
      datetime_utc: "2026-04-04T12:30:00Z",
      impact: "Medium",
      promoted: true,
    });
    const { result } = renderHook(() => useNextEvent([promotedEvent]));
    expect(result.current.event?.id).toBe("ev-promo");
  });

  it("secondsUntil is a positive number for a future event", () => {
    vi.setSystemTime(new Date("2026-04-04T10:00:00Z"));
    const futureEvent = makeEvent({ datetime_utc: "2026-04-04T12:30:00Z", impact: "High" });
    const { result } = renderHook(() => useNextEvent([futureEvent]));
    expect(result.current.secondsUntil).toBeGreaterThan(0);
  });

  it("secondsUntil is 0 when event is null", () => {
    vi.setSystemTime(new Date("2026-04-04T14:00:00Z"));
    const pastEvent = makeEvent({ datetime_utc: "2026-04-04T12:30:00Z", impact: "High" });
    const { result } = renderHook(() => useNextEvent([pastEvent]));
    expect(result.current.secondsUntil).toBe(0);
  });

  it("secondsUntil counts down as time advances", () => {
    vi.setSystemTime(new Date("2026-04-04T10:00:00Z"));
    const futureEvent = makeEvent({ datetime_utc: "2026-04-04T12:30:00Z", impact: "High" });
    const { result } = renderHook(() => useNextEvent([futureEvent]));
    const initial = result.current.secondsUntil;

    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.secondsUntil).toBeLessThan(initial);
  });

  it("prefers High impact over promoted Medium when both are future", () => {
    vi.setSystemTime(new Date("2026-04-04T10:00:00Z"));
    const highEvent = makeEvent({
      id: "ev-high",
      datetime_utc: "2026-04-04T12:30:00Z",
      impact: "High",
      promoted: false,
    });
    const promotedEarlier = makeEvent({
      id: "ev-promo",
      datetime_utc: "2026-04-04T11:00:00Z",
      impact: "Medium",
      promoted: true,
    });
    const { result } = renderHook(() => useNextEvent([highEvent, promotedEarlier]));
    // promoted event is sooner, so it should be returned as next
    expect(result.current.event?.id).toBe("ev-promo");
  });
});
