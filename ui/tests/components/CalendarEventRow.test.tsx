import { describe, it, expect, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";

import { CalendarEventRow } from "@/components/CalendarEventRow";

import type { CalendarEvent } from "@/lib/types";

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
    previous: "0.3%",
    forecast: "0.4%",
    actual: null,
    beat_miss: "pending",
    session_bucket: "cash_session",
    ...overrides,
  };
}

describe("CalendarEventRow", () => {
  it("shows beat symbol when outcome is beat", () => {
    const event = makeEvent({ actual: "0.5%", beat_miss: "beat" });
    render(<CalendarEventRow event={event} context="forex" isPast={false} />);
    expect(screen.getByText(/▲/)).toBeInTheDocument();
  });

  it("shows miss symbol when outcome is miss", () => {
    const event = makeEvent({ actual: "0.2%", beat_miss: "miss" });
    render(<CalendarEventRow event={event} context="forex" isPast={false} />);
    expect(screen.getByText(/▼/)).toBeInTheDocument();
  });

  it("shows dash when outcome is pending", () => {
    const event = makeEvent({ actual: null, beat_miss: "pending" });
    render(<CalendarEventRow event={event} context="forex" isPast={false} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders event name", () => {
    render(<CalendarEventRow event={makeEvent()} context="forex" isPast={false} />);
    expect(screen.getByText("CPI m/m")).toBeInTheDocument();
  });

  it("renders event currency", () => {
    render(<CalendarEventRow event={makeEvent()} context="forex" isPast={false} />);
    expect(screen.getByText("USD")).toBeInTheDocument();
  });

  it("past rows render with reduced opacity", () => {
    render(<CalendarEventRow event={makeEvent()} context="forex" isPast={true} />);
    const row = screen.getByRole("row");
    expect(row.className).toContain("opacity-50");
  });

  it("non-past rows render without reduced opacity", () => {
    render(<CalendarEventRow event={makeEvent()} context="forex" isPast={false} />);
    const row = screen.getByRole("row");
    expect(row.className).not.toContain("opacity-50");
  });

  it("renders promoted badge text for promoted events", () => {
    const event = makeEvent({ promoted: true, impact: "Medium" });
    render(<CalendarEventRow event={event} context="forex" isPast={false} />);
    expect(screen.getByText("promo")).toBeInTheDocument();
  });

  it("does not render promoted badge for non-promoted events", () => {
    render(<CalendarEventRow event={makeEvent({ promoted: false })} context="forex" isPast={false} />);
    expect(screen.queryByText("promo")).not.toBeInTheDocument();
  });

  it("shows actual value text when beat", () => {
    const event = makeEvent({ actual: "0.5%", beat_miss: "beat" });
    render(<CalendarEventRow event={event} context="forex" isPast={false} />);
    expect(screen.getByText(/0\.5%/)).toBeInTheDocument();
  });

  it("shows actual value text when miss", () => {
    const event = makeEvent({ actual: "0.2%", beat_miss: "miss" });
    render(<CalendarEventRow event={event} context="forex" isPast={false} />);
    expect(screen.getByText(/0\.2%/)).toBeInTheDocument();
  });
});
