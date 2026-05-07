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
  total_pnl_pips: 320.5,
  total_pnl_usd: 1250.75,
  best_trade_pnl: 85.2,
  worst_trade_pnl: -42.1,
  current_streak: 3,
  profit_factor: 2.1,
  avg_hold_time_hours: 4.5,
  avg_win_pips: null,
  avg_loss_pips: null,
  avg_win_usd: null,
  avg_loss_usd: null,
  expectancy_usd: null,
  expectancy_pips: null,
  consistency_ratio: null,
  by_strategy: {},
  by_symbol: {},
  by_account: {},
  by_day_of_week: {},
  by_session: {},
  by_confidence: {},
  by_rating: {},
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

  it("still shows Win Rate and Streak in backtest mode", () => {
    render(<StatsBar stats={MOCK_STATS} loading={false} mode="backtest" />);
    expect(screen.getByText("Win Rate")).toBeInTheDocument();
    expect(screen.getByText("Streak")).toBeInTheDocument();
  });
});
