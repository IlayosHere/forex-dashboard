import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import React from "react";

import { CollapsibleSection } from "@/components/CollapsibleSection";

describe("CollapsibleSection — default (collapsible)", () => {
  it("shows the summary and hides children when collapsed", () => {
    render(
      <CollapsibleSection title="Pre-Market" summary="bullish · 1 scenario" expanded={false} onToggle={vi.fn()}>
        <p>child content</p>
      </CollapsibleSection>,
    );
    expect(screen.getByText("bullish · 1 scenario")).toBeInTheDocument();
    expect(screen.queryByText("child content")).not.toBeInTheDocument();
  });

  it("hides the summary and shows children when expanded", () => {
    render(
      <CollapsibleSection title="Pre-Market" summary="bullish · 1 scenario" expanded={true} onToggle={vi.fn()}>
        <p>child content</p>
      </CollapsibleSection>,
    );
    expect(screen.queryByText("bullish · 1 scenario")).not.toBeInTheDocument();
    expect(screen.getByText("child content")).toBeInTheDocument();
  });

  it("calls onToggle when the header is clicked", () => {
    const onToggle = vi.fn();
    render(
      <CollapsibleSection title="Pre-Market" summary="—" expanded={false} onToggle={onToggle}>
        <p>child content</p>
      </CollapsibleSection>,
    );
    fireEvent.click(screen.getByText("Pre-Market"));
    expect(onToggle).toHaveBeenCalled();
  });
});

describe("CollapsibleSection — collapsible=false", () => {
  it("shows children when the caller passes expanded=true (review mode)", () => {
    render(
      <CollapsibleSection title="Pre-Market" summary="—" expanded={true} onToggle={vi.fn()} collapsible={false}>
        <p>child content</p>
      </CollapsibleSection>,
    );
    expect(screen.getByText("child content")).toBeInTheDocument();
  });

  it("renders the header as a non-button (no toggle affordance)", () => {
    render(
      <CollapsibleSection title="Pre-Market" summary="—" expanded={true} onToggle={vi.fn()} collapsible={false}>
        <p>child content</p>
      </CollapsibleSection>,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
