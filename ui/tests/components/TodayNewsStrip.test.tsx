import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import { TodayNewsStrip } from "@/components/TodayNewsStrip";

import type { CalendarEvent, MarketClosure } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  fetchCalendar: vi.fn(),
  fetchMarketHolidays: vi.fn(),
}));

import { fetchCalendar, fetchMarketHolidays } from "@/lib/api";

// "now" must be fixed so PAST_EVENT below stays reliably in the past and
// TODAY_EVENT stays reliably upcoming relative to it.
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

// datetime_utc and datetime_et must agree — "upcoming vs. past" reads
// datetime_utc, while "is this today" reads datetime_et.
const TODAY_EVENT = makeEvent({
  id: "today-1",
  datetime_et: "2026-04-04T20:30:00-04:00", // after NOW (10:00 ET) — upcoming
  datetime_utc: "2026-04-05T00:30:00.000Z",
});
const TOMORROW_EVENT = makeEvent({
  id: "tomorrow-1",
  name: "CPI m/m",
  datetime_et: "2026-04-05T08:30:00-04:00",
  datetime_utc: "2026-04-05T12:30:00.000Z",
});
// Regression fixture for the JOLTS case: released earlier today (before NOW),
// promoted Medium -> High. Must still show, not fall back to "no news today".
const PAST_EVENT = makeEvent({
  id: "past-1",
  name: "JOLTS Job Openings",
  impact: "Medium",
  promoted: true,
  datetime_et: "2026-04-04T08:30:00-04:00", // before NOW (10:00 ET) — already released
  datetime_utc: "2026-04-04T12:30:00.000Z",
});
// Plain Medium, not promoted — must still show (badge supports Medium).
const MEDIUM_EVENT = makeEvent({
  id: "medium-1",
  name: "Factory Orders m/m",
  impact: "Medium",
  promoted: false,
  datetime_et: "2026-04-04T20:30:00-04:00",
  datetime_utc: "2026-04-05T00:30:00.000Z",
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

  it("still shows an already-released event today, instead of a false empty state", async () => {
    // Regression: the strip used to only look at upcoming events, so once
    // today's news released it silently disappeared.
    vi.mocked(fetchCalendar).mockResolvedValue([PAST_EVENT]);
    render(<TodayNewsStrip date="2026-04-04" />);
    await waitFor(() => expect(screen.getByText("JOLTS Job Openings")).toBeInTheDocument());
    expect(screen.queryByText("No high-impact news today")).not.toBeInTheDocument();
  });

  it("shows a plain Medium-impact event (not just promoted ones)", async () => {
    vi.mocked(fetchCalendar).mockResolvedValue([MEDIUM_EVENT]);
    render(<TodayNewsStrip date="2026-04-04" />);
    await waitFor(() => expect(screen.getByText("Factory Orders m/m")).toBeInTheDocument());
    expect(screen.getByText("Medium")).toBeInTheDocument();
  });

  it("prefers the upcoming event over an already-released one on the same day", async () => {
    vi.mocked(fetchCalendar).mockResolvedValue([PAST_EVENT, TODAY_EVENT]);
    render(<TodayNewsStrip date="2026-04-04" />);
    await waitFor(() => expect(screen.getByText("Non-Farm Payrolls")).toBeInTheDocument());
    expect(screen.queryByText("JOLTS Job Openings")).not.toBeInTheDocument();
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
