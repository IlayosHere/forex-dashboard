import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";

import { CalendarNextStrip } from "@/components/CalendarNextStrip";

import type { CalendarEvent, MarketClosure } from "@/lib/types";

afterEach(() => {
  vi.restoreAllMocks();
});

const MOCK_EVENT: CalendarEvent = {
  id: "ev-1",
  name: "Non-Farm Payrolls",
  currency: "USD",
  datetime_utc: "2026-04-04T12:30:00Z",
  datetime_et: "2026-04-04T08:30:00Z",
  impact: "High",
  promoted: false,
  previous: "151K",
  forecast: "180K",
  actual: null,
  beat_miss: "pending",
  session_bucket: "cash_session",
};

describe("CalendarNextStrip", () => {
  it("renders nothing when event prop is null", () => {
    const { container } = render(
      <CalendarNextStrip event={null} secondsUntil={3600} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows event name when event is provided", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3600} />
    );
    expect(screen.getByText("Non-Farm Payrolls")).toBeInTheDocument();
  });

  it("shows event currency when event is provided", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3600} />
    );
    expect(screen.getByText("USD")).toBeInTheDocument();
  });

  it("displays countdown in HH:MM:SS format", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3661} />
    );
    expect(screen.getByText("01:01:01")).toBeInTheDocument();
  });

  it("displays countdown with zero-padded hours and minutes", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3665} />
    );
    expect(screen.getByText("01:01:05")).toBeInTheDocument();
  });

  it("shows RELEASING NOW text when secondsUntil is at threshold (300)", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={300} />
    );
    expect(screen.getByText("RELEASING NOW")).toBeInTheDocument();
  });

  it("shows RELEASING NOW text when secondsUntil is below threshold", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={60} />
    );
    expect(screen.getByText("RELEASING NOW")).toBeInTheDocument();
  });

  it("shows countdown text when secondsUntil is above threshold", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={301} />
    );
    expect(screen.queryByText("RELEASING NOW")).not.toBeInTheDocument();
    expect(screen.getByText("00:05:01")).toBeInTheDocument();
  });

  it("shows ET time suffix", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3600} />
    );
    expect(screen.getByText(/ET/)).toBeInTheDocument();
  });
});

const FULL_CLOSE: MarketClosure = {
  id: "cl-1",
  date: "2026-12-25",
  label: "CME Globex — Christmas Day",
  closure_type: "full_close",
  early_close_et: null,
  note: "No signals will be generated today.",
};

const EARLY_CLOSE: MarketClosure = {
  ...FULL_CLOSE,
  id: "cl-2",
  closure_type: "early_close",
  early_close_et: "13:15",
  label: "CME Globex — July 3rd",
};

describe("CalendarNextStrip — closure override", () => {
  it("renders the closed banner instead of the countdown when closure is full_close", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3600} closure={FULL_CLOSE} />
    );
    expect(screen.getByText("Closed")).toBeInTheDocument();
    expect(screen.getByText("CME Globex — Christmas Day")).toBeInTheDocument();
    expect(screen.queryByText("Non-Farm Payrolls")).not.toBeInTheDocument();
  });

  it("renders nothing when closure is full_close and there is no event either", () => {
    render(<CalendarNextStrip event={null} secondsUntil={0} closure={FULL_CLOSE} />);
    expect(screen.getByText("Closed")).toBeInTheDocument();
  });

  it("shows an early-close badge alongside the normal countdown", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3600} closure={EARLY_CLOSE} />
    );
    expect(screen.getByText(/Early close/)).toBeInTheDocument();
    expect(screen.getByText("Non-Farm Payrolls")).toBeInTheDocument();
  });

  it("does not render a closure badge when closure prop is null", () => {
    render(<CalendarNextStrip event={MOCK_EVENT} secondsUntil={3600} closure={null} />);
    expect(screen.queryByText(/Early close/)).not.toBeInTheDocument();
    expect(screen.queryByText("Closed")).not.toBeInTheDocument();
  });
});
