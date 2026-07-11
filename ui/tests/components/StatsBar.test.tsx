import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { StatsBar } from "@/components/StatsBar";

import type { TradeStats } from "@/lib/types";

const MOCK_STATS: TradeStats = {
  total_trades: 42,
  open_trades: 3,
  closed_trades: 39,
  wins: 25,
  losses: 12,
  breakevens: 2,
  win_rate: 67.6,
  avg_rr: 1.85,
  total_pnl_points: 320.5,
  total_pnl_usd: 1250.75,
  best_trade_pnl: 85.2,
  worst_trade_pnl: -42.1,
  current_streak: 3,
  profit_factor: 2.1,
  avg_hold_time_hours: 4.5,
  avg_win_points: null,
  avg_loss_points: null,
  avg_win_usd: null,
  avg_loss_usd: null,
  expectancy_usd: null,
  expectancy_points: null,
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

describe("StatsBar", () => {
  it("renders all stat card titles", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} />);
    expect(screen.getByText("Win Rate")).toBeInTheDocument();
    expect(screen.getByText("Trades")).toBeInTheDocument();
    expect(screen.getByText("P&L")).toBeInTheDocument();
    expect(screen.getByText("Avg R:R")).toBeInTheDocument();
    expect(screen.getByText("Streak")).toBeInTheDocument();
    expect(screen.getByText("Profit Factor")).toBeInTheDocument();
  });

  it("renders win rate percentage", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} />);
    expect(screen.getByText("67.6%")).toBeInTheDocument();
  });

  it("renders total trades count", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} />);
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders win/loss secondary text", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} />);
    expect(screen.getByText("25W 12L")).toBeInTheDocument();
  });

  it("renders winning streak as W3", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} />);
    expect(screen.getByText("W3")).toBeInTheDocument();
  });

  it("renders losing streak as L2", () => {
    const losingStats = { ...MOCK_STATS, current_streak: -2 };
    render(<StatsBar stats={losingStats} loading={false} />);
    expect(screen.getByText("L2")).toBeInTheDocument();
  });

  it("renders profit factor", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} />);
    expect(screen.getByText("2.10")).toBeInTheDocument();
  });

  it("renders avg R:R", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} />);
    expect(screen.getByText("1.85")).toBeInTheDocument();
  });

  it("renders dashes when stats is null", () => {
    render(<StatsBar stats={null} loading={false} />);
    const dashes = screen.getAllByText("\u2014");
    expect(dashes.length).toBeGreaterThan(0);
  });

  it("applies opacity when loading", () => {
    const { container } = render(<StatsBar stats={null} loading={true} />);
    const wrapper = container.firstElementChild;
    expect(wrapper?.className).toContain("opacity-50");
  });

  it("shows open trades count in secondary", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} />);
    expect(screen.getByText("3 open")).toBeInTheDocument();
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("StatsBar — BeOutcomeCard", () => {
  it("renders BE Quality card when be_outcome_breakdown has counts", () => {
    const stats = {
      ...MOCK_STATS,
      be_outcome_breakdown: { prevented_loss: 3, missed_tp: 1, unreviewed: 1 },
    };
    render(<StatsBar stats={stats} loading={false} />);
    expect(screen.getByText("BE Quality")).toBeInTheDocument();
  });

  it("computes saved percentage from prevented_loss / total", () => {
    const stats = {
      ...MOCK_STATS,
      be_outcome_breakdown: { prevented_loss: 3, missed_tp: 1, unreviewed: 0 },
    };
    render(<StatsBar stats={stats} loading={false} />);
    expect(screen.getByText("75% saved")).toBeInTheDocument();
  });

  it("renders secondary breakdown text with correct counts", () => {
    const stats = {
      ...MOCK_STATS,
      be_outcome_breakdown: { prevented_loss: 2, missed_tp: 1, unreviewed: 1 },
    };
    render(<StatsBar stats={stats} loading={false} />);
    expect(screen.getByText(/2↓ 1↑/)).toBeInTheDocument();
  });

  it("shows unreviewed count in secondary when unreviewed > 0", () => {
    const stats = {
      ...MOCK_STATS,
      be_outcome_breakdown: { prevented_loss: 2, missed_tp: 1, unreviewed: 3 },
    };
    render(<StatsBar stats={stats} loading={false} />);
    expect(screen.getByText(/3\?/)).toBeInTheDocument();
  });

  it("does not render BE Quality card when all counts are 0", () => {
    const stats = {
      ...MOCK_STATS,
      be_outcome_breakdown: { prevented_loss: 0, missed_tp: 0, unreviewed: 0 },
    };
    render(<StatsBar stats={stats} loading={false} />);
    expect(screen.queryByText("BE Quality")).not.toBeInTheDocument();
  });

  it("does not render BE Quality card when be_outcome_breakdown is absent", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} />);
    expect(screen.queryByText("BE Quality")).not.toBeInTheDocument();
  });
});

describe("StatsBar — backtest mode", () => {
  it("shows P&L (notional) title in backtest mode", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} mode="backtest" />);
    expect(screen.getByText("P&L (notional)")).toBeInTheDocument();
    expect(screen.queryByText("P&L")).not.toBeInTheDocument();
  });

  it("shows plain P&L title in default mode", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} mode="default" />);
    expect(screen.getByText("P&L")).toBeInTheDocument();
    expect(screen.queryByText("P&L (notional)")).not.toBeInTheDocument();
  });

  it("renders Avg R:R before Trades in backtest mode", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} mode="backtest" />);
    const allTitles = screen.getAllByText(/Win Rate|Avg R:R|Trades|P&L/);
    const texts = allTitles.map((el) => el.textContent);
    const rrIdx = texts.indexOf("Avg R:R");
    const tradesIdx = texts.indexOf("Trades");
    expect(rrIdx).toBeLessThan(tradesIdx);
  });

  it("renders Trades before Avg R:R in default mode", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} mode="default" />);
    const allTitles = screen.getAllByText(/Win Rate|Avg R:R|Trades|P&L/);
    const texts = allTitles.map((el) => el.textContent);
    const rrIdx = texts.indexOf("Avg R:R");
    const tradesIdx = texts.indexOf("Trades");
    expect(tradesIdx).toBeLessThan(rrIdx);
  });

  it("shows Win Rate but not Streak in backtest mode", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} mode="backtest" />);
    expect(screen.getByText("Win Rate")).toBeInTheDocument();
    expect(screen.queryByText("Streak")).not.toBeInTheDocument();
  });

  it("shows Criteria Met card in backtest mode", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} mode="backtest" />);
    expect(screen.getByText("Criteria Met")).toBeInTheDocument();
  });

  it("shows Compliance card in live mode, not in backtest", () => {
    const { rerender } = render(<StatsBar stats={MOCK_STATS} loading={false} mode="default" />);
    expect(screen.getByText("Compliance")).toBeInTheDocument();
    expect(screen.queryByText("Criteria Met")).not.toBeInTheDocument();

    rerender(<StatsBar stats={MOCK_STATS} loading={false} mode="backtest" />);
    expect(screen.queryByText("Compliance")).not.toBeInTheDocument();
    expect(screen.getByText("Criteria Met")).toBeInTheDocument();
  });

  it("computes Criteria Met rate from by_criteria_met", () => {
    const stats = {
      ...MOCK_STATS,
      by_criteria_met: {
        met: { total: 7, wins: 5, losses: 2, win_rate: 71.4, total_pnl_points: 0, total_pnl_usd: 350, avg_pnl_usd: 50, avg_rr: 1.8, name: "met" },
        not_met: { total: 3, wins: 1, losses: 2, win_rate: 33.3, total_pnl_points: 0, total_pnl_usd: -50, avg_pnl_usd: -16.7, avg_rr: 0.6, name: "not_met" },
      },
    };
    render(<StatsBar stats={stats} loading={false} mode="backtest" />);
    expect(screen.getByText("70%")).toBeInTheDocument();
    expect(screen.getByText("7 met / 3 not")).toBeInTheDocument();
  });

  it("shows 'not recorded' when no criteria_met data", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} mode="backtest" />);
    expect(screen.getByText("not recorded")).toBeInTheDocument();
  });

  it("omits $ from P&L value in backtest mode", () => {
    const { container } = render(<StatsBar stats={MOCK_STATS} loading={false} mode="backtest" />);
    const pnlCard = screen.getByText("P&L (notional)").closest("div");
    expect(pnlCard?.textContent).not.toContain("$");
  });

  it("includes $ in P&L value in live mode", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} mode="default" />);
    // The P&L card renders "P&L" label and value like "+$1250.75" in sibling divs
    const pnlLabel = screen.getByText("P&L");
    const card = pnlLabel.closest(".border.border-border.rounded");
    expect(card?.textContent).toContain("$");
  });
});
