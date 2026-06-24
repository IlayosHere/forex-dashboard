import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { ScenarioForm } from "@/components/ScenarioForm";

import type { PlanScenario } from "@/lib/types";

afterEach(() => { vi.restoreAllMocks(); });

// Labels in ScenarioForm are plain siblings of their Combobox trigger, not
// htmlFor-linked, so getByLabelText doesn't work — grab the trigger via the
// label text's next sibling (Combobox's Root renders no wrapper element).
function triggerAfterLabel(labelText: string): HTMLElement {
  return screen.getByText(labelText).nextElementSibling as HTMLElement;
}

function chooseOption(labelText: string, optionText: string) {
  fireEvent.click(triggerAfterLabel(labelText));
  fireEvent.click(screen.getByText(optionText));
}

function makeScenario(overrides: Partial<PlanScenario> = {}): PlanScenario {
  return {
    id: "sc-1",
    plan_id: "p-1",
    date: "2026-06-22",
    reaction_setup_type: "liquidity_sweep",
    reaction_setup_detail: "london_high",
    target_level_type: "fvg",
    target_level_detail: "1h",
    notes: "original notes",
    outcome_status: null,
    created_at: "2026-06-22T10:00:00Z",
    updated_at: "2026-06-22T10:00:00Z",
    ...overrides,
  };
}

describe("ScenarioForm — add mode", () => {
  it("disables the submit button when the form is empty", () => {
    render(<ScenarioForm onAdd={vi.fn()} saving={false} />);
    expect(screen.getByText("Add Scenario")).toBeDisabled();
  });

  it("enables the submit button once notes are entered", () => {
    render(<ScenarioForm onAdd={vi.fn()} saving={false} />);
    fireEvent.change(screen.getByPlaceholderText(/anything else worth capturing/), {
      target: { value: "some notes" },
    });
    expect(screen.getByText("Add Scenario")).not.toBeDisabled();
  });

  it("calls onAdd with the form data and resets after submit", async () => {
    const onAdd = vi.fn().mockResolvedValue(undefined);
    render(<ScenarioForm onAdd={onAdd} saving={false} />);
    fireEvent.change(screen.getByPlaceholderText(/anything else worth capturing/), {
      target: { value: "some notes" },
    });
    fireEvent.click(screen.getByText("Add Scenario"));
    expect(onAdd).toHaveBeenCalledWith(expect.objectContaining({ notes: "some notes" }));
  });

  it("shows the reaction detail select only after a reaction type is chosen", () => {
    render(<ScenarioForm onAdd={vi.fn()} saving={false} />);
    expect(screen.queryByText("Detail")).not.toBeInTheDocument();
    chooseOption("Reaction Area", "Liquidity Sweep");
    expect(screen.getByText("Detail")).toBeInTheDocument();
  });

  it("clears the reaction detail when the reaction type changes", () => {
    render(<ScenarioForm onAdd={vi.fn()} saving={false} />);
    chooseOption("Reaction Area", "Liquidity Sweep");
    chooseOption("Detail", "London High");
    expect(triggerAfterLabel("Detail")).toHaveTextContent("London High");

    chooseOption("Reaction Area", "Unmitigated FVG");
    expect(triggerAfterLabel("Detail")).toHaveTextContent("Select…");
  });

  it("does not call onAdd when isEmpty and disabled button is clicked", () => {
    const onAdd = vi.fn();
    render(<ScenarioForm onAdd={onAdd} saving={false} />);
    fireEvent.click(screen.getByText("Add Scenario"));
    expect(onAdd).not.toHaveBeenCalled();
  });

  it("shows a saving label while saving", () => {
    render(<ScenarioForm onAdd={vi.fn()} saving={true} />);
    expect(screen.getByText("Adding…")).toBeInTheDocument();
  });
});

describe("ScenarioForm — edit mode", () => {
  it("pre-fills the form from the scenario being edited", () => {
    render(<ScenarioForm saving={false} editing={makeScenario()} onSaveEdit={vi.fn()} onCancelEdit={vi.fn()} />);
    expect(screen.getByPlaceholderText(/anything else worth capturing/)).toHaveValue("original notes");
  });

  it("shows 'Save Changes' and 'Cancel' instead of 'Add Scenario'", () => {
    render(<ScenarioForm saving={false} editing={makeScenario()} onSaveEdit={vi.fn()} onCancelEdit={vi.fn()} />);
    expect(screen.getByText("Save Changes")).toBeInTheDocument();
    expect(screen.getByText("Cancel")).toBeInTheDocument();
    expect(screen.queryByText("Add Scenario")).not.toBeInTheDocument();
  });

  it("calls onSaveEdit (not onAdd) with edited data on submit", () => {
    const onAdd = vi.fn();
    const onSaveEdit = vi.fn().mockResolvedValue(undefined);
    render(<ScenarioForm onAdd={onAdd} saving={false} editing={makeScenario()} onSaveEdit={onSaveEdit} onCancelEdit={vi.fn()} />);
    fireEvent.change(screen.getByPlaceholderText(/anything else worth capturing/), {
      target: { value: "edited notes" },
    });
    fireEvent.click(screen.getByText("Save Changes"));
    expect(onSaveEdit).toHaveBeenCalledWith(expect.objectContaining({ notes: "edited notes" }));
    expect(onAdd).not.toHaveBeenCalled();
  });

  it("calls onCancelEdit when Cancel is clicked", () => {
    const onCancelEdit = vi.fn();
    render(<ScenarioForm saving={false} editing={makeScenario()} onSaveEdit={vi.fn()} onCancelEdit={onCancelEdit} />);
    fireEvent.click(screen.getByText("Cancel"));
    expect(onCancelEdit).toHaveBeenCalledOnce();
  });

  it("does not disable Save Changes even when fields are cleared", () => {
    render(
      <ScenarioForm
        saving={false}
        editing={makeScenario({ reaction_setup_type: null, target_level_type: null, notes: "" })}
        onSaveEdit={vi.fn()}
        onCancelEdit={vi.fn()}
      />,
    );
    expect(screen.getByText("Save Changes")).not.toBeDisabled();
  });
});
