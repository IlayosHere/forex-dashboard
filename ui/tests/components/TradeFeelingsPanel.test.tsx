import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { TradeFeelingsPanel } from "@/components/TradeFeelingsPanel";

afterEach(() => { vi.restoreAllMocks(); });

const noop = vi.fn();

describe("TradeFeelingsPanel — labels", () => {
  it("renders Before, During, and After labels", () => {
    render(
      <TradeFeelingsPanel
        feelingBefore={null}
        feelingDuring={null}
        feelingAfter={null}
        onChange={noop}
      />
    );
    expect(screen.getByText("Before")).toBeInTheDocument();
    expect(screen.getByText("During")).toBeInTheDocument();
    expect(screen.getByText("After")).toBeInTheDocument();
  });

  it("renders the Feelings section heading", () => {
    render(
      <TradeFeelingsPanel
        feelingBefore={null}
        feelingDuring={null}
        feelingAfter={null}
        onChange={noop}
      />
    );
    expect(screen.getByText("Feelings")).toBeInTheDocument();
  });
});

describe("TradeFeelingsPanel — interaction", () => {
  it("calls onChange with feeling_before when a before-row pill is clicked", () => {
    const onChange = vi.fn();
    render(
      <TradeFeelingsPanel
        feelingBefore={null}
        feelingDuring={null}
        feelingAfter={null}
        onChange={onChange}
      />
    );
    // "Calm" appears 3 times (once per row) — click the first one (Before row)
    fireEvent.click(screen.getAllByText("Calm")[0]);
    expect(onChange).toHaveBeenCalledWith("feeling_before", "calm");
  });

  it("calls onChange with feeling_during for the second row", () => {
    const onChange = vi.fn();
    render(
      <TradeFeelingsPanel
        feelingBefore={null}
        feelingDuring={null}
        feelingAfter={null}
        onChange={onChange}
      />
    );
    fireEvent.click(screen.getAllByText("Focused")[1]);
    expect(onChange).toHaveBeenCalledWith("feeling_during", "focused");
  });

  it("calls onChange with feeling_after for the third row", () => {
    const onChange = vi.fn();
    render(
      <TradeFeelingsPanel
        feelingBefore={null}
        feelingDuring={null}
        feelingAfter={null}
        onChange={onChange}
      />
    );
    fireEvent.click(screen.getAllByText("Confident")[2]);
    expect(onChange).toHaveBeenCalledWith("feeling_after", "confident");
  });
});
