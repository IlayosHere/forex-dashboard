import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { EdgeMetrics } from "@/components/stats/EdgeMetrics";
import type { TradeStats } from "@/lib/types";

const BASE_STATS: TradeStats = {
  total_trades: 40,
  open_trades: 1,
  closed_trades: 39,
  wins: 24,
  losses: 12,
  breakevens: 3,
  win_rate: 66.7,
  avg_rr: 1.6,
  total_pnl_pips: 300,
  total_pnl_usd: 1800,
  best_trade_pnl: 100,
  worst_trade_pnl: -50,
  current_streak: 2,
  profit_factor: 1.9,
  avg_hold_time_hours: 2.5,
  avg_win_pips: 25,
  avg_loss_pips: 15,
  avg_win_usd: 75,
  avg_loss_usd: -45,
  expectancy_usd: 36,
  expectancy_pips: 6,
  consistency_ratio: 72,
  by_strategy: {},
  by_symbol: {},
  by_account: {},
  by_day_of_week: {},
  by_session: {},
  by_confidence: {},
  by_rating: {},
};

describe("EdgeMetrics — live mode", () => {
  it("shows Expectancy card, not Edge Margin", () => {
    render(<EdgeMetrics stats={BASE_STATS} loading={false} isBacktest={false} />);
    expect(screen.getByText("Expectancy")).toBeInTheDocument();
    expect(screen.queryByText("Edge Margin")).not.toBeInTheDocument();
  });

  it("shows Rule Compliance card, not Criteria Compliance", () => {
    render(<EdgeMetrics stats={BASE_STATS} loading={false} isBacktest={false} />);
    expect(screen.getByText("Rule Compliance")).toBeInTheDocument();
    expect(screen.queryByText("Criteria Compliance")).not.toBeInTheDocument();
  });

  it("shows USD expectancy value", () => {
    render(<EdgeMetrics stats={BASE_STATS} loading={false} isBacktest={false} />);
    expect(screen.getByText("+$36.00")).toBeInTheDocument();
  });

  it("shows compliance rate from by_rule_compliance", () => {
    const stats = {
      ...BASE_STATS,
      by_rule_compliance: {
        compliant: { total: 8, wins: 6, losses: 2, win_rate: 75, total_pnl_usd: 400, avg_rr: 2.1 },
        mistake: { total: 2, wins: 0, losses: 2, win_rate: 0, total_pnl_usd: -100, avg_rr: 0.5 },
      },
    };
    render(<EdgeMetrics stats={stats} loading={false} isBacktest={false} />);
    expect(screen.getByText("80%")).toBeInTheDocument();
    expect(screen.getByText("8 ok / 2 mistakes")).toBeInTheDocument();
  });

  it("shows WR comparison row when both buckets have win_rate", () => {
    const stats = {
      ...BASE_STATS,
      by_rule_compliance: {
        compliant: { total: 8, wins: 6, losses: 2, win_rate: 75, total_pnl_usd: 400, avg_rr: 2.1 },
        mistake: { total: 2, wins: 0, losses: 2, win_rate: 0, total_pnl_usd: -100, avg_rr: 0.5 },
      },
    };
    render(<EdgeMetrics stats={stats} loading={false} isBacktest={false} />);
    expect(screen.getByText(/WR — ok vs mistakes/)).toBeInTheDocument();
  });

  it("shows consistency % with definition sub-text", () => {
    render(<EdgeMetrics stats={BASE_STATS} loading={false} isBacktest={false} />);
    expect(screen.getByText("72.0%")).toBeInTheDocument();
    expect(screen.getByText("% of weeks net positive")).toBeInTheDocument();
  });

  it("applies opacity-50 when loading", () => {
    const { container } = render(<EdgeMetrics stats={BASE_STATS} loading={true} isBacktest={false} />);
    expect(container.firstElementChild?.className).toContain("opacity-50");
  });
});

describe("EdgeMetrics — backtest mode", () => {
  it("shows Edge Margin card, not Expectancy", () => {
    render(<EdgeMetrics stats={BASE_STATS} loading={false} isBacktest={true} />);
    expect(screen.getAllByText("Edge Margin").length).toBeGreaterThan(0);
    expect(screen.queryByText("Expectancy")).not.toBeInTheDocument();
  });

  it("shows Criteria Compliance card, not Rule Compliance", () => {
    render(<EdgeMetrics stats={BASE_STATS} loading={false} isBacktest={true} />);
    expect(screen.getByText("Criteria Compliance")).toBeInTheDocument();
    expect(screen.queryByText("Rule Compliance")).not.toBeInTheDocument();
  });

  it("computes breakeven WR from avg_rr=1.6 → 38.5%", () => {
    // 1/(1+1.6)*100 = 38.46% → 38.5
    render(<EdgeMetrics stats={BASE_STATS} loading={false} isBacktest={true} />);
    expect(screen.getByText("38.5%")).toBeInTheDocument();
  });

  it("shows positive edge margin", () => {
    // WR 66.7 - BE 38.5 = +28.2pp
    render(<EdgeMetrics stats={BASE_STATS} loading={false} isBacktest={true} />);
    expect(screen.getByText("+28.2pp")).toBeInTheDocument();
    expect(screen.getByText("comfortable edge")).toBeInTheDocument();
  });

  it("shows negative edge margin label when WR below breakeven", () => {
    render(
      <EdgeMetrics
        stats={{ ...BASE_STATS, win_rate: 30, avg_rr: 1.6 }}
        loading={false}
        isBacktest={true}
      />,
    );
    expect(screen.getByText("negative edge")).toBeInTheDocument();
  });

  it("shows criteria compliance rate from by_criteria_met", () => {
    const stats = {
      ...BASE_STATS,
      by_criteria_met: {
        met: { total: 7, wins: 5, losses: 2, win_rate: 71.4, total_pnl_usd: 350, avg_rr: 1.9 },
        not_met: { total: 3, wins: 1, losses: 2, win_rate: 33.3, total_pnl_usd: -50, avg_rr: 0.7 },
      },
    };
    render(<EdgeMetrics stats={stats} loading={false} isBacktest={true} />);
    expect(screen.getByText("70%")).toBeInTheDocument();
    expect(screen.getByText("7 met / 3 not met")).toBeInTheDocument();
  });

  it("shows Avg R delta between met and not-met buckets", () => {
    const stats = {
      ...BASE_STATS,
      by_criteria_met: {
        met: { total: 7, wins: 5, losses: 2, win_rate: 71.4, total_pnl_usd: 350, avg_rr: 2.0 },
        not_met: { total: 3, wins: 1, losses: 2, win_rate: 33.3, total_pnl_usd: -50, avg_rr: 0.8 },
      },
    };
    render(<EdgeMetrics stats={stats} loading={false} isBacktest={true} />);
    expect(screen.getByText(/\+1\.20R when criteria honored/)).toBeInTheDocument();
  });

  it("shows 'not recorded' when no criteria_met data", () => {
    render(<EdgeMetrics stats={BASE_STATS} loading={false} isBacktest={true} />);
    expect(screen.getByText("not recorded")).toBeInTheDocument();
  });

  it("renders without crash when stats is null", () => {
    render(<EdgeMetrics stats={null} loading={false} isBacktest={true} />);
    expect(screen.getAllByText("Edge Margin").length).toBeGreaterThan(0);
  });
});
