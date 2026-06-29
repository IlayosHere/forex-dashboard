import { describe, it, expect } from "vitest";

import { ALL_TABS, buildRows } from "@/components/stats/unifiedBreakdownsHelpers";
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
  total_pnl_points: 100,
  total_pnl_usd: 500,
  best_trade_pnl: 100,
  worst_trade_pnl: -50,
  current_streak: 1,
  profit_factor: 1.5,
  avg_hold_time_hours: 2,
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
  by_news_day: {
    normal: {
      total: 6, wins: 3, losses: 3, win_rate: 50, total_pnl_points: 0,
      total_pnl_usd: -50, avg_pnl_usd: -8.3, avg_rr: -0.5, total_r: -3,
      name: "Normal day",
    },
    high: {
      total: 3, wins: 3, losses: 0, win_rate: 100, total_pnl_points: 0,
      total_pnl_usd: 300, avg_pnl_usd: 100, avg_rr: 3, total_r: 9,
      name: "High-impact news day",
    },
    medium: {
      total: 1, wins: 0, losses: 1, win_rate: 0, total_pnl_points: 0,
      total_pnl_usd: -50, avg_pnl_usd: -50, avg_rr: -1, total_r: -1,
      name: "Medium-impact news day",
    },
  },
  by_market_holiday: {
    normal: {
      total: 9, wins: 6, losses: 3, win_rate: 66.7, total_pnl_points: 0,
      total_pnl_usd: 250, avg_pnl_usd: 27.8, avg_rr: 0.5, total_r: 4.5,
      name: "Normal day",
    },
    thin_volume: {
      total: 1, wins: 0, losses: 1, win_rate: 0, total_pnl_points: 0,
      total_pnl_usd: -50, avg_pnl_usd: -50, avg_rr: -1, total_r: -1,
      name: "Thin volume",
    },
  },
};

describe("unifiedBreakdownsHelpers — news_day / market_holiday tabs", () => {
  it("registers both tabs without an ICT requirement — available in live and backtest mode", () => {
    const newsDay = ALL_TABS.find((t) => t.key === "news_day");
    const marketHoliday = ALL_TABS.find((t) => t.key === "market_holiday");
    expect(newsDay?.requiresIct).toBe(false);
    expect(marketHoliday?.requiresIct).toBe(false);
  });

  it("sorts news_day rows by severity (high, medium, normal), not P&L or alphabetically", () => {
    const rows = buildRows("news_day", BASE_STATS, null);
    expect(rows.map((r) => r.key)).toEqual(["high", "medium", "normal"]);
  });

  it("sorts market_holiday rows by severity (full_close, early_close, thin_volume, normal)", () => {
    const rows = buildRows("market_holiday", BASE_STATS, null);
    expect(rows.map((r) => r.key)).toEqual(["thin_volume", "normal"]);
  });

  it("uses the backend-provided descriptive name as the row label", () => {
    const rows = buildRows("news_day", BASE_STATS, null);
    const high = rows.find((r) => r.key === "high");
    expect(high?.label).toBe("High-impact news day");
  });

  it("returns an empty list when stats is null", () => {
    expect(buildRows("news_day", null, null)).toEqual([]);
    expect(buildRows("market_holiday", null, null)).toEqual([]);
  });

  it("nulls win-rate/avg-R/expectancy for buckets below the 5-decisive-trade floor, but keeps the count", () => {
    const rows = buildRows("news_day", BASE_STATS, null);
    // "high" bucket: wins=3, losses=0 → 3 decisive trades, below the floor.
    const high = rows.find((r) => r.key === "high");
    expect(high?.total).toBe(3);
    expect(high?.winRate).toBeNull();
    expect(high?.avgRr).toBeNull();
  });

  it("keeps win-rate/avg-R for buckets at or above the 5-decisive-trade floor", () => {
    const rows = buildRows("news_day", BASE_STATS, null);
    // "normal" bucket: wins=3, losses=3 → 6 decisive trades, at/above the floor.
    const normal = rows.find((r) => r.key === "normal");
    expect(normal?.winRate).toBe(50);
    expect(normal?.avgRr).toBe(-0.5);
  });

  it("does not apply the sample floor to other tabs (e.g. day_of_week)", () => {
    const statsWithSmallDayBucket: TradeStats = {
      ...BASE_STATS,
      by_day_of_week: {
        "0": {
          total: 1, wins: 1, losses: 0, win_rate: 100, total_pnl_points: 0,
          total_pnl_usd: 50, avg_pnl_usd: 50, avg_rr: 1, name: "Monday",
        },
      },
    };
    const rows = buildRows("day_of_week", statsWithSmallDayBucket, null);
    expect(rows[0].winRate).toBe(100);
  });
});
