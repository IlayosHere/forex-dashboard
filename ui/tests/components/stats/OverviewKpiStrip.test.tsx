import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { OverviewKpiStrip } from "@/components/stats/OverviewKpiStrip";
import type { TradeStats } from "@/lib/types";

const BASE_STATS: TradeStats = {
  total_trades: 50,
  open_trades: 2,
  closed_trades: 48,
  wins: 30,
  losses: 15,
  breakevens: 3,
  win_rate: 66.7,
  avg_rr: 1.8,
  total_pnl_points: 400,
  total_pnl_usd: 2400,
  best_trade_pnl: 120,
  worst_trade_pnl: -60,
  current_streak: 3,
  profit_factor: 2.1,
  avg_hold_time_hours: 3.5,
  avg_win_points: null,
  avg_loss_points: null,
  avg_win_usd: null,
  avg_loss_usd: null,
  expectancy_usd: 48.0,
  expectancy_points: 8.0,
  consistency_ratio: null,
  by_strategy: {},
  by_symbol: {},
  by_account: {},
  by_day_of_week: {},
  by_session: {},
  by_confidence: {},
  by_rating: {},
  by_news_day: {},
  by_market_holiday: {},
};

describe("OverviewKpiStrip — live mode", () => {
  it("renders 5-column grid", () => {
    const { container } = render(
      <OverviewKpiStrip stats={BASE_STATS} loading={false} isBacktest={false} />,
    );
    expect(container.firstElementChild?.className).toContain("grid-cols-5");
  });

  it("shows Expectancy tile (USD) as first tile", () => {
    render(<OverviewKpiStrip stats={BASE_STATS} loading={false} isBacktest={false} />);
    expect(screen.getByText("Expectancy")).toBeInTheDocument();
    expect(screen.queryByText("Expectancy R")).not.toBeInTheDocument();
  });

  it("shows Net P&L tile", () => {
    render(<OverviewKpiStrip stats={BASE_STATS} loading={false} isBacktest={false} />);
    expect(screen.getByText("Net P&L")).toBeInTheDocument();
  });

  it("shows $-prefixed P&L value in live mode", () => {
    render(<OverviewKpiStrip stats={BASE_STATS} loading={false} isBacktest={false} />);
    expect(screen.getByText("+$2400.00")).toBeInTheDocument();
  });

  it("shows profit factor threshold sub-text", () => {
    render(<OverviewKpiStrip stats={BASE_STATS} loading={false} isBacktest={false} />);
    expect(screen.getByText("above threshold")).toBeInTheDocument();
  });

  it("renders '--' for all tiles when stats is null", () => {
    render(<OverviewKpiStrip stats={null} loading={false} isBacktest={false} />);
    const dashes = screen.getAllByText("--");
    expect(dashes.length).toBeGreaterThan(0);
  });

  it("applies opacity-50 when loading", () => {
    const { container } = render(
      <OverviewKpiStrip stats={BASE_STATS} loading={true} isBacktest={false} />,
    );
    expect(container.firstElementChild?.className).toContain("opacity-50");
  });
});

describe("OverviewKpiStrip — backtest mode", () => {
  it("renders 4-column grid", () => {
    const { container } = render(
      <OverviewKpiStrip stats={BASE_STATS} loading={false} isBacktest={true} />,
    );
    expect(container.firstElementChild?.className).toContain("grid-cols-4");
  });

  it("shows Expectancy R tile, not Expectancy USD", () => {
    render(<OverviewKpiStrip stats={BASE_STATS} loading={false} isBacktest={true} />);
    expect(screen.getByText("Expectancy R")).toBeInTheDocument();
    expect(screen.queryByText("Expectancy")).not.toBeInTheDocument();
  });

  it("does not show Net P&L tile", () => {
    render(<OverviewKpiStrip stats={BASE_STATS} loading={false} isBacktest={true} />);
    expect(screen.queryByText("Net P&L")).not.toBeInTheDocument();
  });

  it("computes Expectancy R correctly (66.7% WR × 1.8R)", () => {
    // E(R) = (0.667 * 1.8) - (1 - 0.667) = 1.2006 - 0.333 = 0.87 (rounded to 2dp)
    render(<OverviewKpiStrip stats={BASE_STATS} loading={false} isBacktest={true} />);
    expect(screen.getByText("+0.87R")).toBeInTheDocument();
  });

  it("shows '--' for Expectancy R when avg_rr is null", () => {
    render(
      <OverviewKpiStrip
        stats={{ ...BASE_STATS, avg_rr: null }}
        loading={false}
        isBacktest={true}
      />,
    );
    const dashes = screen.getAllByText("--");
    expect(dashes.length).toBeGreaterThan(0);
  });

  it("shows 'below 1.5' sub-text when profit factor below threshold", () => {
    render(
      <OverviewKpiStrip
        stats={{ ...BASE_STATS, profit_factor: 1.2 }}
        loading={false}
        isBacktest={true}
      />,
    );
    expect(screen.getByText("below 1.5")).toBeInTheDocument();
  });
});
