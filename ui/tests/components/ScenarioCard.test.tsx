import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { ScenarioCard } from "@/components/ScenarioCard";

import type { PlanScenario } from "@/lib/types";

afterEach(() => { vi.restoreAllMocks(); });

function makeScenario(overrides: Partial<PlanScenario> = {}): PlanScenario {
  return {
    id: "sc-1",
    plan_id: "p-1",
    date: "2026-06-22",
    reaction_setup_type: "liquidity_sweep",
    reaction_setup_detail: "london_high",
    target_level_type: "fvg",
    target_level_detail: "1h",
    notes: "watch for reversal",
    outcome_status: null,
    created_at: "2026-06-22T10:00:00Z",
    updated_at: "2026-06-22T10:00:00Z",
    ...overrides,
  };
}

const noop = {
  onEdit: vi.fn(),
  onSaveEdit: vi.fn(),
  onCancelEdit: vi.fn(),
  onDelete: vi.fn(),
  onSetOutcome: vi.fn(),
};

describe("ScenarioCard — read-only view", () => {
  it("renders the scenario's area, target, and notes", () => {
    render(<ScenarioCard scenario={makeScenario()} index={0} saving={false} isEditing={false} {...noop} />);
    expect(screen.getByText("liquidity_sweep · london_high")).toBeInTheDocument();
    expect(screen.getByText("fvg · 1h")).toBeInTheDocument();
    expect(screen.getByText("watch for reversal")).toBeInTheDocument();
  });

  it("numbers the scenario using the index prop", () => {
    render(<ScenarioCard scenario={makeScenario()} index={2} saving={false} isEditing={false} {...noop} />);
    expect(screen.getByText("Scenario 3")).toBeInTheDocument();
  });

  it("omits rows for unset fields", () => {
    render(
      <ScenarioCard
        scenario={makeScenario({ reaction_setup_type: null, reaction_setup_detail: null, notes: "" })}
        index={0}
        saving={false}
        isEditing={false}
        {...noop}
      />,
    );
    expect(screen.queryByText("Area")).not.toBeInTheDocument();
    expect(screen.queryByText("Notes")).not.toBeInTheDocument();
  });

  it("calls onEdit when Edit is clicked", () => {
    const onEdit = vi.fn();
    render(<ScenarioCard scenario={makeScenario()} index={0} saving={false} isEditing={false} {...noop} onEdit={onEdit} />);
    fireEvent.click(screen.getByText("Edit"));
    expect(onEdit).toHaveBeenCalledOnce();
  });

  it("calls onDelete with the scenario id when Delete is clicked", () => {
    const onDelete = vi.fn();
    render(<ScenarioCard scenario={makeScenario()} index={0} saving={false} isEditing={false} {...noop} onDelete={onDelete} />);
    fireEvent.click(screen.getByText("Delete"));
    expect(onDelete).toHaveBeenCalledWith("sc-1");
  });

  it("links 'Log Trade' to /journal/new with the scenario id, MNQ strategy, and live account_type by default", () => {
    render(<ScenarioCard scenario={makeScenario()} index={0} saving={false} isEditing={false} {...noop} />);
    expect(screen.getByText(/Log Trade/).closest("a")).toHaveAttribute(
      "href",
      "/journal/new?scenario=sc-1&strategy=mnq-daily&account_type=live",
    );
  });

  it("shows no active outcome pill by default", () => {
    render(<ScenarioCard scenario={makeScenario()} index={0} saving={false} isEditing={false} {...noop} />);
    expect(screen.getByText("Played Out")).toBeInTheDocument();
    expect(screen.getByText("Invalidated")).toBeInTheDocument();
  });

  it("calls onSetOutcome with the chosen value", () => {
    const onSetOutcome = vi.fn();
    render(<ScenarioCard scenario={makeScenario()} index={0} saving={false} isEditing={false} {...noop} onSetOutcome={onSetOutcome} />);
    fireEvent.click(screen.getByText("Played Out"));
    expect(onSetOutcome).toHaveBeenCalledWith("sc-1", "played_out");
  });

  it("clicking the already-active outcome pill clears it", () => {
    const onSetOutcome = vi.fn();
    render(<ScenarioCard scenario={makeScenario({ outcome_status: "invalidated" })} index={0} saving={false} isEditing={false} {...noop} onSetOutcome={onSetOutcome} />);
    fireEvent.click(screen.getByText("Invalidated"));
    expect(onSetOutcome).toHaveBeenCalledWith("sc-1", null);
  });
});

describe("ScenarioCard — editing view", () => {
  it("renders the ScenarioForm pre-filled instead of the read-only rows when isEditing", () => {
    render(<ScenarioCard scenario={makeScenario()} index={0} saving={false} isEditing={true} {...noop} />);
    expect(screen.getByText("Editing Scenario 1")).toBeInTheDocument();
    expect(screen.getByDisplayValue("watch for reversal")).toBeInTheDocument();
    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
  });
});
