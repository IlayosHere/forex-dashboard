import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import { UnifiedBreakdowns } from "@/components/stats/UnifiedBreakdowns";
import type { TradeStats } from "@/lib/types";

const BASE_STATS: TradeStats = {
  total_trades: 10,
  open_trades: 0,
  closed_trades: 10,
  wins: 6,
  losses: 4,
  breakevens: 0,
  win_rate: 60,
  avg_rr: 1.2,
  total_pnl_pips: 100,
  total_pnl_usd: 500,
  best_trade_pnl: 100,
  worst_trade_pnl: -50,
  current_streak: 1,
  profit_factor: 1.5,
  avg_hold_time_hours: 2,
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
  by_news_day: {},
  by_market_holiday: {},
  news_data_coverage_through: "2026-05-28",
  holiday_data_coverage_through: "2026-12-31",
};

describe("UnifiedBreakdowns — News Day / Market Holiday tabs", () => {
  it("shows both tabs without an account-type gate", () => {
    render(<UnifiedBreakdowns stats={BASE_STATS} ictStats={null} loading={false} />);
    expect(screen.getByText("News Day")).toBeTruthy();
    expect(screen.getByText("Market Holiday")).toBeTruthy();
  });

  it("does not show a caption on the default Session tab", () => {
    render(<UnifiedBreakdowns stats={BASE_STATS} ictStats={null} loading={false} />);
    expect(screen.queryByText(/Data verified through/)).toBeNull();
  });

  it("shows the backtest framing + coverage date on the News Day tab in backtest mode", () => {
    render(<UnifiedBreakdowns stats={BASE_STATS} ictStats={null} loading={false} isBacktest />);
    fireEvent.click(screen.getByText("News Day"));
    expect(screen.getByText(/Retrospective check/)).toBeTruthy();
    expect(screen.getByText(/Data verified through 2026-05-28/)).toBeTruthy();
  });

  it("shows the small-sample framing on the News Day tab in live mode", () => {
    render(<UnifiedBreakdowns stats={BASE_STATS} ictStats={null} loading={false} isBacktest={false} />);
    fireEvent.click(screen.getByText("News Day"));
    expect(screen.getByText(/Small live sample/)).toBeTruthy();
  });

  it("shows the holiday coverage date on the Market Holiday tab", () => {
    render(<UnifiedBreakdowns stats={BASE_STATS} ictStats={null} loading={false} isBacktest />);
    fireEvent.click(screen.getByText("Market Holiday"));
    expect(screen.getByText(/Data verified through 2026-12-31/)).toBeTruthy();
  });
});
