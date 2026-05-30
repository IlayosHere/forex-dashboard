import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { WeekSummaryCell } from "@/components/WeekSummaryCell";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("WeekSummaryCell — ISO week label", () => {
  it("renders 'Wk' when no weekDate is provided", () => {
    render(<WeekSummaryCell pnl={0} pnlR={0} showMoney={false} tradeCount={0} wins={0} losses={0} />);
    expect(screen.getByText("Wk")).toBeInTheDocument();
  });

  it("renders W16 for Monday 2026-04-13 (mid-April)", () => {
    render(
      <WeekSummaryCell pnl={0} pnlR={0} showMoney={false} tradeCount={0} wins={0} losses={0} weekDate="2026-04-13" />
    );
    expect(screen.getByText("W16")).toBeInTheDocument();
  });

  it("renders W1 for 2026-01-01 (Thursday — belongs to week 1 of 2026)", () => {
    render(
      <WeekSummaryCell pnl={0} pnlR={0} showMoney={false} tradeCount={0} wins={0} losses={0} weekDate="2026-01-01" />
    );
    expect(screen.getByText("W1")).toBeInTheDocument();
  });

  it("renders W53 for 2026-12-31 (Thursday — last week of 2026)", () => {
    render(
      <WeekSummaryCell pnl={0} pnlR={0} showMoney={false} tradeCount={0} wins={0} losses={0} weekDate="2026-12-31" />
    );
    expect(screen.getByText("W53")).toBeInTheDocument();
  });

  it("never renders W0 or W54 for any boundary date", () => {
    const boundaryCases = ["2026-01-01", "2026-12-31", "2025-12-29", "2025-01-01"];
    for (const date of boundaryCases) {
      const { unmount } = render(
        <WeekSummaryCell pnl={0} pnlR={0} showMoney={false} tradeCount={0} wins={0} losses={0} weekDate={date} />
      );
      expect(screen.queryByText("W0")).not.toBeInTheDocument();
      expect(screen.queryByText("W54")).not.toBeInTheDocument();
      unmount();
    }
  });

  it("renders W1 for 2025-12-29 (Monday — ISO week belongs to 2026 week 1)", () => {
    // 2025-12-29 is a Monday; its Thursday is 2026-01-01 → belongs to ISO week 1 of 2026
    render(
      <WeekSummaryCell pnl={0} pnlR={0} showMoney={false} tradeCount={0} wins={0} losses={0} weekDate="2025-12-29" />
    );
    expect(screen.getByText("W1")).toBeInTheDocument();
  });
});

describe("WeekSummaryCell — trade summary display", () => {
  it("shows no P&L when tradeCount is 0", () => {
    render(
      <WeekSummaryCell pnl={150} pnlR={1.5} showMoney={true} tradeCount={0} wins={0} losses={0} weekDate="2026-04-13" />
    );
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("shows positive P&L with + prefix when tradeCount > 0", () => {
    render(
      <WeekSummaryCell pnl={250} pnlR={2.5} showMoney={true} tradeCount={3} wins={2} losses={1} weekDate="2026-04-13" />
    );
    expect(screen.getByText("+$250")).toBeInTheDocument();
  });

  it("shows negative P&L with - prefix", () => {
    render(
      <WeekSummaryCell pnl={-100} pnlR={-1} showMoney={true} tradeCount={2} wins={0} losses={2} weekDate="2026-04-13" />
    );
    expect(screen.getByText("-$100")).toBeInTheDocument();
  });

  it("shows R value by default (showMoney=false)", () => {
    render(
      <WeekSummaryCell pnl={250} pnlR={2.5} showMoney={false} tradeCount={3} wins={2} losses={1} weekDate="2026-04-13" />
    );
    expect(screen.getByText("+2.50R")).toBeInTheDocument();
  });

  it("shows wins and losses record", () => {
    render(
      <WeekSummaryCell pnl={50} pnlR={0.5} showMoney={false} tradeCount={3} wins={2} losses={1} weekDate="2026-04-13" />
    );
    expect(screen.getByText("2W 1L")).toBeInTheDocument();
  });

  it("hides W/L record when no trades", () => {
    render(
      <WeekSummaryCell pnl={0} pnlR={0} showMoney={false} tradeCount={0} wins={0} losses={0} weekDate="2026-04-13" />
    );
    expect(screen.queryByText(/W \d+L/)).not.toBeInTheDocument();
  });
});
