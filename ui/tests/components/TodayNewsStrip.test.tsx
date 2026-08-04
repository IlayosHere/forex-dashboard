import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { TodayNewsStrip } from "@/components/TodayNewsStrip";

import type { CalendarEvent, MarketClosure } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  fetchCalendar: vi.fn(),
  fetchMarketHolidays: vi.fn(),
}));

import { fetchCalendar, fetchMarketHolidays } from "@/lib/api";

// useNextEvent only surfaces upcoming events, so "now" must be fixed and
// earlier than TODAY_EVENT below — real wall-clock time would eventually
// make this event "past" and break the test.
const NOW = new Date("2026-04-04T10:00:00-04:00");

beforeEach(() => {
  // Only fake Date — faking setTimeout too would freeze waitFor's polling.
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(NOW);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

function makeEvent(overrides: Partial<CalendarEvent> = {}): CalendarEvent {
  return {
    id: "ev-1",
    name: "Non-Farm Payrolls",
    currency: "USD",
    datetime_utc: "2026-04-04T12:30:00Z",
    datetime_et: "2026-04-04T08:30:00-04:00",
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

// datetime_utc and datetime_et must agree — useNextEvent's "is this upcoming"
// check reads datetime_utc, while this component's "is this today" check
// reads datetime_et.
const TODAY_EVENT = makeEvent({
  id: "today-1",
  datetime_et: "2026-04-04T20:30:00-04:00",
  datetime_utc: "2026-04-05T00:30:00.000Z",
});
const TOMORROW_EVENT = makeEvent({
  id: "tomorrow-1",
  name: "CPI m/m",
  datetime_et: "2026-04-05T08:30:00-04:00",
  datetime_utc: "2026-04-05T12:30:00.000Z",
});

describe("TodayNewsStrip", () => {
  beforeEach(() => {
    vi.mocked(fetchMarketHolidays).mockResolvedValue([]);
  });

  it("shows today's high-impact event", async () => {
    vi.mocked(fetchCalendar).mockResolvedValue([TODAY_EVENT, TOMORROW_EVENT]);
    render(<TodayNewsStrip date="2026-04-04" />);
    await waitFor(() => expect(screen.getByText("Non-Farm Payrolls")).toBeInTheDocument());
    expect(screen.queryByText("CPI m/m")).not.toBeInTheDocument();
  });

  it("shows the empty state when today has no high/medium-impact event", async () => {
    vi.mocked(fetchCalendar).mockResolvedValue([TOMORROW_EVENT]);
    render(<TodayNewsStrip date="2026-04-04" />);
    await waitFor(() =>
      expect(screen.getByText("No high-impact news today")).toBeInTheDocument()
    );
  });

  it("never shows the live countdown/pulse treatment", async () => {
    vi.mocked(fetchCalendar).mockResolvedValue([TODAY_EVENT]);
    render(<TodayNewsStrip date="2026-04-04" />);
    await waitFor(() => expect(screen.getByText("Non-Farm Payrolls")).toBeInTheDocument());
    expect(screen.queryByText("RELEASING NOW")).not.toBeInTheDocument();
  });

  it("links to /calendar", async () => {
    vi.mocked(fetchCalendar).mockResolvedValue([TODAY_EVENT]);
    render(<TodayNewsStrip date="2026-04-04" />);
    await waitFor(() => expect(screen.getByRole("link")).toHaveAttribute("href", "/calendar"));
  });
});

const FULL_CLOSE: MarketClosure = {
  id: "cl-1",
  date: "2026-04-04",
  label: "CME Globex — Good Friday",
  closure_type: "full_close",
  early_close_et: null,
  note: "No signals will be generated today.",
};

describe("TodayNewsStrip — closure override", () => {
  it("renders the closed banner instead of an event when today is a full closure", async () => {
    vi.mocked(fetchCalendar).mockResolvedValue([TODAY_EVENT]);
    vi.mocked(fetchMarketHolidays).mockResolvedValue([FULL_CLOSE]);
    render(<TodayNewsStrip date="2026-04-04" />);
    await waitFor(() => expect(screen.getByText("Closed")).toBeInTheDocument());
    expect(screen.queryByText("Non-Farm Payrolls")).not.toBeInTheDocument();
  });
});
