import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { StatusBadge } from "@/components/StatusBadge";

describe("StatusBadge", () => {
  it("renders Open with pulse indicator for open status", () => {
    render(<StatusBadge status="open" outcome={null} />);
    expect(screen.getByText("Open")).toBeInTheDocument();
  });

  it("renders Cancelled with line-through for cancelled status", () => {
    render(<StatusBadge status="cancelled" outcome={null} />);
    const el = screen.getByText("Cancelled");
    expect(el).toBeInTheDocument();
    expect(el.className).toContain("line-through");
  });

  it("renders Win for closed status with win outcome", () => {
    render(<StatusBadge status="closed" outcome="win" />);
    expect(screen.getByText("Win")).toBeInTheDocument();
  });

  it("renders Loss for closed status with loss outcome", () => {
    render(<StatusBadge status="closed" outcome="loss" />);
    expect(screen.getByText("Loss")).toBeInTheDocument();
  });

  it("renders BE for closed status with breakeven outcome", () => {
    render(<StatusBadge status="closed" outcome="breakeven" />);
    expect(screen.getByText("BE")).toBeInTheDocument();
  });

  it("renders BE when status is closed and outcome is null", () => {
    render(<StatusBadge status="closed" outcome={null} />);
    expect(screen.getByText("BE")).toBeInTheDocument();
  });

  it("renders Win with green color", () => {
    render(<StatusBadge status="closed" outcome="win" />);
    const el = screen.getByText("Win");
    expect(el.className).toContain("text-[#26a69a]");
  });

  it("renders Loss with red color", () => {
    render(<StatusBadge status="closed" outcome="loss" />);
    const el = screen.getByText("Loss");
    expect(el.className).toContain("text-[#ef5350]");
  });
});
