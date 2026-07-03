import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { CalendarFilters } from "@/components/CalendarFilters";

import type { CalendarImpact } from "@/lib/types";

afterEach(() => {
  vi.restoreAllMocks();
});

interface DefaultProps {
  week: "current" | "next";
  onWeekChange: (w: "current" | "next") => void;
  impactFilter: CalendarImpact[];
  onImpactChange: (impacts: CalendarImpact[]) => void;
}

function defaultProps(): DefaultProps {
  return {
    week: "current",
    onWeekChange: vi.fn() as (w: "current" | "next") => void,
    impactFilter: ["High"],
    onImpactChange: vi.fn() as (impacts: CalendarImpact[]) => void,
  };
}

describe("CalendarFilters", () => {
  it("renders High impact pill", () => {
    render(<CalendarFilters {...defaultProps()} />);
    expect(screen.getByRole("button", { name: "High" })).toBeInTheDocument();
  });

  it("renders Med impact pill", () => {
    render(<CalendarFilters {...defaultProps()} />);
    expect(screen.getByRole("button", { name: "Med" })).toBeInTheDocument();
  });

  it("renders Low impact pill", () => {
    render(<CalendarFilters {...defaultProps()} />);
    expect(screen.getByRole("button", { name: "Low" })).toBeInTheDocument();
  });

  it("clicking High impact pill calls onImpactChange", () => {
    const props = defaultProps();
    render(<CalendarFilters {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "High" }));
    expect(props.onImpactChange).toHaveBeenCalled();
  });

  it("clicking Med impact pill calls onImpactChange with Medium toggled in", () => {
    const props = defaultProps();
    render(<CalendarFilters {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "Med" }));
    expect(props.onImpactChange).toHaveBeenCalledWith(["High", "Medium"]);
  });

  it("clicking Low impact pill calls onImpactChange with Low toggled in", () => {
    const props = defaultProps();
    render(<CalendarFilters {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "Low" }));
    expect(props.onImpactChange).toHaveBeenCalledWith(["High", "Low"]);
  });

  it("Reset filters button is NOT visible when defaults are active", () => {
    render(<CalendarFilters {...defaultProps()} />);
    expect(screen.queryByRole("button", { name: "Reset filters" })).not.toBeInTheDocument();
  });

  it("Reset filters button IS visible when week is next", () => {
    render(<CalendarFilters {...defaultProps()} week="next" />);
    expect(screen.getByRole("button", { name: "Reset filters" })).toBeInTheDocument();
  });

  it("Reset filters button IS visible when impactFilter has extra items", () => {
    render(
      <CalendarFilters {...defaultProps()} impactFilter={["High", "Medium"]} />
    );
    expect(screen.getByRole("button", { name: "Reset filters" })).toBeInTheDocument();
  });

  it("clicking Reset filters resets week to current", () => {
    const props = defaultProps();
    render(<CalendarFilters {...props} week="next" />);
    fireEvent.click(screen.getByRole("button", { name: "Reset filters" }));
    expect(props.onWeekChange).toHaveBeenCalledWith("current");
  });

  it("clicking Reset filters resets impact to High only", () => {
    const props = defaultProps();
    render(<CalendarFilters {...props} impactFilter={["High", "Medium"]} />);
    fireEvent.click(screen.getByRole("button", { name: "Reset filters" }));
    expect(props.onImpactChange).toHaveBeenCalledWith(["High"]);
  });
});
