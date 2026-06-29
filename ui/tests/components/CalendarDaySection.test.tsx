import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";

import { CalendarDaySection } from "@/components/CalendarDaySection";

import type { MarketClosure } from "@/lib/types";

afterEach(() => {
  vi.restoreAllMocks();
});

function makeClosure(overrides: Partial<MarketClosure> = {}): MarketClosure {
  return {
    id: "cl-1",
    date: "2026-12-25",
    label: "CME Globex — Christmas Day",
    closure_type: "full_close",
    early_close_et: null,
    note: "No signals will be generated today.",
    ...overrides,
  };
}

describe("CalendarDaySection — closures", () => {
  it("shows no badge when there are no closures", () => {
    render(
      <CalendarDaySection
        date="2026-12-23"
        events={[]}
        closures={[]}
        defaultOpen={false}
        currentTime={new Date("2026-12-23T00:00:00Z")}
      />
    );
    expect(screen.queryByText("Closed")).not.toBeInTheDocument();
    expect(screen.queryByText("Holiday")).not.toBeInTheDocument();
  });

  it("shows a Closed badge and auto-expands when a full_close closure is present", () => {
    render(
      <CalendarDaySection
        date="2026-12-25"
        events={[]}
        closures={[makeClosure()]}
        defaultOpen={false}
        currentTime={new Date("2026-12-25T00:00:00Z")}
      />
    );
    expect(screen.getByText("Closed")).toBeInTheDocument();
    // auto-expanded despite defaultOpen={false} — the closure row is visible
    expect(screen.getByText("CME Globex — Christmas Day")).toBeInTheDocument();
  });

  it("shows a Holiday badge and stays collapsed for a thin_volume-only day", () => {
    render(
      <CalendarDaySection
        date="2026-06-19"
        events={[]}
        closures={[makeClosure({ closure_type: "thin_volume", label: "NQ — Juneteenth National Independence Day" })]}
        defaultOpen={false}
        currentTime={new Date("2026-06-19T00:00:00Z")}
      />
    );
    expect(screen.getByText("Holiday")).toBeInTheDocument();
    expect(screen.queryByText("NQ — Juneteenth National Independence Day")).not.toBeInTheDocument();
  });
});
