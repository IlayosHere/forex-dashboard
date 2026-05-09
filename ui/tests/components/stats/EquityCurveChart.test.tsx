import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { EquityCurveChart } from "@/components/stats/EquityCurveChart";
import type { EquityCurvePoint } from "@/lib/types";

function makePoint(cumulative: number, pnl: number, outcome: string): EquityCurvePoint {
  return {
    date: "2025-03-10",
    close_time: "2025-03-10T10:00:00Z",
    pnl_usd: pnl,
    pnl_pips: pnl * 2,
    cumulative_pnl_usd: cumulative,
    cumulative_pnl_pips: cumulative * 2,
    trade_count: 1,
    outcome,
  };
}

const SAMPLE_DATA = [
  makePoint(100, 100, "win"),
  makePoint(50, -50, "loss"),
  makePoint(125, 75, "win"),
];

describe("EquityCurveChart — live mode", () => {
  it("renders without crash on valid data", () => {
    const { container } = render(
      <EquityCurveChart data={SAMPLE_DATA} loading={false} isBacktest={false} />,
    );
    expect(container.firstElementChild).toBeInTheDocument();
  });

  it("does not show notional disclaimer in live mode", () => {
    render(<EquityCurveChart data={SAMPLE_DATA} loading={false} isBacktest={false} />);
    expect(screen.queryByText(/Notional P&L/i)).not.toBeInTheDocument();
  });

  it("renders without crash on empty data", () => {
    const { container } = render(
      <EquityCurveChart data={[]} loading={false} isBacktest={false} />,
    );
    expect(container.firstElementChild).toBeInTheDocument();
  });

  it("applies opacity-50 when loading", () => {
    const { container } = render(
      <EquityCurveChart data={SAMPLE_DATA} loading={true} isBacktest={false} />,
    );
    expect(container.firstElementChild?.className).toContain("opacity-50");
  });
});

describe("EquityCurveChart — backtest mode", () => {
  it("shows notional P&L disclaimer", () => {
    render(<EquityCurveChart data={SAMPLE_DATA} loading={false} isBacktest={true} />);
    expect(screen.getByText(/Notional P&L/i)).toBeInTheDocument();
  });

  it("does not show notional disclaimer in live mode", () => {
    render(<EquityCurveChart data={SAMPLE_DATA} loading={false} isBacktest={false} />);
    expect(screen.queryByText(/Notional P&L/i)).not.toBeInTheDocument();
  });

  it("renders without crash on empty data in backtest mode", () => {
    const { container } = render(
      <EquityCurveChart data={[]} loading={false} isBacktest={true} />,
    );
    expect(container.firstElementChild).toBeInTheDocument();
  });
});
