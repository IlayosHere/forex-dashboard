import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { MonthlyBars } from "@/components/stats/MonthlyBars";
import type { DailySummaryPoint } from "@/lib/types";

function makeDay(date: string, pnl_usd: number): DailySummaryPoint {
  return {
    date,
    trades: 1,
    wins: pnl_usd > 0 ? 1 : 0,
    losses: pnl_usd < 0 ? 1 : 0,
    breakevens: 0,
    pnl_usd,
    pnl_points: pnl_usd * 2,
    pnl_r: pnl_usd / 100,
    compliant: 0,
    mistakes: 0,
  };
}

const MARCH_DAYS = [
  makeDay("2025-03-05", 200),
  makeDay("2025-03-12", -80),
];

const MULTI_MONTH = [
  makeDay("2025-03-10", 150),
  makeDay("2025-03-20", 50),
  makeDay("2025-04-05", -100),
];

describe("MonthlyBars — live mode", () => {
  it("shows 'Monthly P&L' header without notional suffix", () => {
    render(<MonthlyBars data={MARCH_DAYS} loading={false} isBacktest={false} />);
    expect(screen.getByText("Monthly P&L")).toBeInTheDocument();
    expect(screen.queryByText(/notional/)).not.toBeInTheDocument();
  });

  it("aggregates daily entries into a single monthly row", () => {
    render(<MonthlyBars data={MULTI_MONTH} loading={false} isBacktest={false} />);
    // March: 150+50=200, April: -100 → two month rows
    expect(screen.getByText("Mar 25")).toBeInTheDocument();
    expect(screen.getByText("Apr 25")).toBeInTheDocument();
  });

  it("prefixes positive P&L with '+'", () => {
    render(<MonthlyBars data={MARCH_DAYS} loading={false} isBacktest={false} />);
    // March net: 200 + (-80) = 120 → "+$120"
    expect(screen.getByText("+$120")).toBeInTheDocument();
  });

  it("includes $ sign in live mode values", () => {
    render(<MonthlyBars data={MARCH_DAYS} loading={false} isBacktest={false} />);
    const positive = screen.getByText("+$120");
    expect(positive.textContent).toContain("$");
  });

  it("shows 'No data' when data is empty", () => {
    render(<MonthlyBars data={[]} loading={false} isBacktest={false} />);
    expect(screen.getByText("No data")).toBeInTheDocument();
  });

  it("applies opacity-50 when loading", () => {
    const { container } = render(<MonthlyBars data={MARCH_DAYS} loading={true} isBacktest={false} />);
    expect(container.firstElementChild?.className).toContain("opacity-50");
  });
});

describe("MonthlyBars — backtest mode", () => {
  it("shows 'Monthly P&L (notional)' header", () => {
    render(<MonthlyBars data={MARCH_DAYS} loading={false} isBacktest={true} />);
    expect(screen.getByText("Monthly P&L (notional)")).toBeInTheDocument();
  });

  it("omits $ from P&L values in backtest mode", () => {
    render(<MonthlyBars data={MARCH_DAYS} loading={false} isBacktest={true} />);
    // Should not find any element with $ in backtest P&L values
    const allText = document.body.textContent ?? "";
    // Remove the header "Monthly P&L (notional)" and check remaining values
    expect(screen.queryByText("+$120")).not.toBeInTheDocument();
    expect(screen.getByText("+120")).toBeInTheDocument();
  });

  it("still shows 'No data' when data is empty", () => {
    render(<MonthlyBars data={[]} loading={false} isBacktest={true} />);
    expect(screen.getByText("No data")).toBeInTheDocument();
  });
});
