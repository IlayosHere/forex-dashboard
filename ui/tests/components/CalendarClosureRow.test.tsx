import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";

import { CalendarClosureRow } from "@/components/CalendarClosureRow";

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

describe("CalendarClosureRow", () => {
  it("renders the closure label", () => {
    render(<CalendarClosureRow closure={makeClosure()} />);
    expect(screen.getByText("CME Globex — Christmas Day")).toBeInTheDocument();
  });

  it("shows CLOSED badge for full_close", () => {
    render(<CalendarClosureRow closure={makeClosure()} />);
    expect(screen.getByText("CLOSED")).toBeInTheDocument();
  });

  it("shows EARLY CLOSE badge and time for early_close", () => {
    const closure = makeClosure({
      closure_type: "early_close",
      early_close_et: "13:15",
      label: "CME Globex — July 3rd",
    });
    render(<CalendarClosureRow closure={closure} />);
    expect(screen.getByText("EARLY CLOSE")).toBeInTheDocument();
    expect(screen.getByText("13:15")).toBeInTheDocument();
  });

  it("shows THIN VOLUME badge for thin_volume", () => {
    const closure = makeClosure({
      closure_type: "thin_volume",
      label: "NQ — Juneteenth National Independence Day",
    });
    render(<CalendarClosureRow closure={closure} />);
    expect(screen.getByText("THIN VOLUME")).toBeInTheDocument();
  });

  it("shows NQ in the currency column", () => {
    render(<CalendarClosureRow closure={makeClosure()} />);
    expect(screen.getByText("NQ")).toBeInTheDocument();
  });

  it("shows dashes for the time and numeric columns when there is no early_close_et", () => {
    render(<CalendarClosureRow closure={makeClosure()} />);
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(4);
  });
});
