import { describe, it, expect, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";

import { CalendarNextStrip } from "@/components/CalendarNextStrip";

import type { CalendarEvent } from "@/lib/types";

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
      <CalendarNextStrip event={null} secondsUntil={3600} context="forex" />
    );
    expect(container.firstChild).toBeNull();
  });

  it("shows event name when event is provided", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3600} context="forex" />
    );
    expect(screen.getByText("Non-Farm Payrolls")).toBeInTheDocument();
  });

  it("shows event currency when event is provided", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3600} context="forex" />
    );
    expect(screen.getByText("USD")).toBeInTheDocument();
  });

  it("displays countdown in HH:MM:SS format", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3661} context="forex" />
    );
    expect(screen.getByText("01:01:01")).toBeInTheDocument();
  });

  it("displays countdown with zero-padded hours and minutes", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3665} context="forex" />
    );
    expect(screen.getByText("01:01:05")).toBeInTheDocument();
  });

  it("shows RELEASING NOW text when secondsUntil is at threshold (300)", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={300} context="forex" />
    );
    expect(screen.getByText("RELEASING NOW")).toBeInTheDocument();
  });

  it("shows RELEASING NOW text when secondsUntil is below threshold", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={60} context="forex" />
    );
    expect(screen.getByText("RELEASING NOW")).toBeInTheDocument();
  });

  it("shows countdown text when secondsUntil is above threshold", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={301} context="forex" />
    );
    expect(screen.queryByText("RELEASING NOW")).not.toBeInTheDocument();
    expect(screen.getByText("00:05:01")).toBeInTheDocument();
  });

  it("shows UTC time suffix when context is forex", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3600} context="forex" />
    );
    expect(screen.getByText(/UTC/)).toBeInTheDocument();
  });

  it("shows ET time suffix when context is mnq", () => {
    render(
      <CalendarNextStrip event={MOCK_EVENT} secondsUntil={3600} context="mnq" />
    );
    expect(screen.getByText(/ET/)).toBeInTheDocument();
  });
});
