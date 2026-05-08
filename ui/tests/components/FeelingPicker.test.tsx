import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { FeelingPicker } from "@/components/FeelingPicker";
import { FEELING_OPTIONS } from "@/lib/feelings";

import type { TradingFeeling } from "@/lib/types";

afterEach(() => { vi.restoreAllMocks(); });

describe("FeelingPicker — rendering", () => {
  it("renders all 10 feeling options", () => {
    render(<FeelingPicker value={null} onChange={vi.fn()} />);
    for (const opt of FEELING_OPTIONS) {
      expect(screen.getByText(opt.label)).toBeInTheDocument();
    }
  });

  it("renders with no option selected when value is null", () => {
    render(<FeelingPicker value={null} onChange={vi.fn()} />);
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(FEELING_OPTIONS.length);
  });
});

describe("FeelingPicker — selection", () => {
  it("calls onChange with the feeling when a pill is clicked", () => {
    const onChange = vi.fn();
    render(<FeelingPicker value={null} onChange={onChange} />);
    fireEvent.click(screen.getByText("Calm"));
    expect(onChange).toHaveBeenCalledWith("calm" satisfies TradingFeeling);
  });

  it("calls onChange with null when the active pill is clicked again (deselect)", () => {
    const onChange = vi.fn();
    render(<FeelingPicker value={"calm"} onChange={onChange} />);
    fireEvent.click(screen.getByText("Calm"));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("calls onChange with a different feeling when a non-active pill is clicked", () => {
    const onChange = vi.fn();
    render(<FeelingPicker value={"calm"} onChange={onChange} />);
    fireEvent.click(screen.getByText("Anxious"));
    expect(onChange).toHaveBeenCalledWith("anxious" satisfies TradingFeeling);
  });
});

describe("FeelingPicker — disabled state", () => {
  it("does not call onChange when disabled", () => {
    const onChange = vi.fn();
    render(<FeelingPicker value={null} onChange={onChange} disabled />);
    fireEvent.click(screen.getByText("Calm"));
    expect(onChange).not.toHaveBeenCalled();
  });
});
