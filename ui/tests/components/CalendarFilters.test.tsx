import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { CalendarFilters } from "@/components/CalendarFilters";

import type { CalendarContext, CalendarImpact } from "@/lib/types";

afterEach(() => {
  vi.restoreAllMocks();
});

interface DefaultProps {
  context: CalendarContext;
  onContextChange: ReturnType<typeof vi.fn>;
  week: "current" | "next";
  onWeekChange: ReturnType<typeof vi.fn>;
  impactFilter: CalendarImpact[];
  onImpactChange: ReturnType<typeof vi.fn>;
  currencyFilter: string;
  onCurrencyChange: ReturnType<typeof vi.fn>;
}

function defaultProps(): DefaultProps {
  return {
    context: "forex",
    onContextChange: vi.fn(),
    week: "current",
    onWeekChange: vi.fn(),
    impactFilter: ["High"],
    onImpactChange: vi.fn(),
    currencyFilter: "All",
    onCurrencyChange: vi.fn(),
  };
}

describe("CalendarFilters", () => {
  it("renders the Forex context button", () => {
    render(<CalendarFilters {...defaultProps()} />);
    expect(screen.getByRole("button", { name: "Forex" })).toBeInTheDocument();
  });

  it("renders the MNQ context button", () => {
    render(<CalendarFilters {...defaultProps()} />);
    expect(screen.getByRole("button", { name: "MNQ" })).toBeInTheDocument();
  });

  it("clicking MNQ calls onContextChange with 'mnq'", () => {
    const props = defaultProps();
    render(<CalendarFilters {...props} />);
    fireEvent.click(screen.getByRole("button", { name: "MNQ" }));
    expect(props.onContextChange).toHaveBeenCalledWith("mnq");
  });

  it("clicking Forex calls onContextChange with 'forex'", () => {
    const props = defaultProps();
    render(<CalendarFilters {...props} context="mnq" />);
    fireEvent.click(screen.getByRole("button", { name: "Forex" }));
    expect(props.onContextChange).toHaveBeenCalledWith("forex");
  });

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

  it("Reset filters button is NOT visible when defaults are active (forex context)", () => {
    render(<CalendarFilters {...defaultProps()} />);
    expect(screen.queryByRole("button", { name: "Reset filters" })).not.toBeInTheDocument();
  });

  it("Reset filters button is NOT visible when defaults are active (mnq context with USD)", () => {
    render(
      <CalendarFilters
        {...defaultProps()}
        context="mnq"
        impactFilter={["High"]}
        currencyFilter="USD"
      />
    );
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

  it("Reset filters button IS visible when currency is non-default", () => {
    render(<CalendarFilters {...defaultProps()} currencyFilter="EUR" />);
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
