import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { BeOutcomeControl } from "@/components/TradeAssessmentPanel";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("BeOutcomeControl — rendering", () => {
  it("renders all three option buttons", () => {
    render(<BeOutcomeControl value={null} onChange={() => {}} />);
    expect(screen.getByText("Not Reviewed")).toBeInTheDocument();
    expect(screen.getByText("Prevented Loss")).toBeInTheDocument();
    expect(screen.getByText("Missed TP")).toBeInTheDocument();
  });

  it("renders the section label", () => {
    render(<BeOutcomeControl value={null} onChange={() => {}} />);
    expect(screen.getByText("Breakeven Outcome")).toBeInTheDocument();
  });

  it("renders sublabels for each option", () => {
    render(<BeOutcomeControl value={null} onChange={() => {}} />);
    expect(screen.getByText("decide later")).toBeInTheDocument();
    expect(screen.getByText("price hit SL anyway")).toBeInTheDocument();
    expect(screen.getByText("price would have won")).toBeInTheDocument();
  });
});

describe("BeOutcomeControl — onChange callbacks", () => {
  it("calls onChange with null when Not Reviewed is clicked", () => {
    const onChange = vi.fn();
    render(<BeOutcomeControl value="prevented_loss" onChange={onChange} />);
    fireEvent.click(screen.getByText("Not Reviewed"));
    expect(onChange).toHaveBeenCalledWith(null);
  });

  it("calls onChange with prevented_loss when Prevented Loss is clicked", () => {
    const onChange = vi.fn();
    render(<BeOutcomeControl value={null} onChange={onChange} />);
    fireEvent.click(screen.getByText("Prevented Loss"));
    expect(onChange).toHaveBeenCalledWith("prevented_loss");
  });

  it("calls onChange with missed_tp when Missed TP is clicked", () => {
    const onChange = vi.fn();
    render(<BeOutcomeControl value={null} onChange={onChange} />);
    fireEvent.click(screen.getByText("Missed TP"));
    expect(onChange).toHaveBeenCalledWith("missed_tp");
  });

  it("calls onChange with null when currently active value is re-clicked via Not Reviewed", () => {
    const onChange = vi.fn();
    render(<BeOutcomeControl value="missed_tp" onChange={onChange} />);
    fireEvent.click(screen.getByText("Not Reviewed"));
    expect(onChange).toHaveBeenCalledWith(null);
  });
});
