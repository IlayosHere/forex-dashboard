"use client";

import { useMemo } from "react";

import type { DailySummaryPoint } from "@/lib/types";

export interface CalendarMonthSummaryProps {
  dailyData: DailySummaryPoint[];
  year: number;
  month: number;
  showMoney: boolean;
}

interface MonthStats {
  netPnl: number;
  netR: number;
  winRate: number | null;
  tradingDays: number;
  totalTrades: number;
}

function computeMonthStats(
  data: DailySummaryPoint[],
  year: number,
  month: number,
): MonthStats {
  const prefix = `${year}-${String(month).padStart(2, "0")}`;
  const filtered = data.filter((d) => d.date.startsWith(prefix));

  let netPnl = 0;
  let netR = 0;
  let totalWins = 0;
  let totalLosses = 0;
  let tradingDays = 0;
  let totalTrades = 0;

  for (const d of filtered) {
    netPnl += d.pnl_usd;
    netR += d.pnl_r;
    totalWins += d.wins;
    totalLosses += d.losses;
    totalTrades += d.trades;
    if (d.trades > 0) tradingDays++;
  }

  const denominator = totalWins + totalLosses;
  const winRate = denominator > 0 ? (totalWins / denominator) * 100 : null;

  return { netPnl, netR, winRate, tradingDays, totalTrades };
}

function formatPnl(pnl: number): string {
  const prefix = pnl >= 0 ? "+$" : "-$";
  return `${prefix}${Math.abs(pnl).toFixed(2)}`;
}

function formatR(r: number): string {
  if (r >= 0) return `+${r.toFixed(2)}R`;
  return `${r.toFixed(2)}R`;
}

export function CalendarMonthSummary({
  dailyData,
  year,
  month,
  showMoney,
}: CalendarMonthSummaryProps) {
  const stats = useMemo(
    () => computeMonthStats(dailyData, year, month),
    [dailyData, year, month],
  );

  const primaryValue = showMoney ? stats.netPnl : stats.netR;
  const primaryColor =
    primaryValue > 0 ? "#26a69a" : primaryValue < 0 ? "#ef5350" : "#e0e0e0";

  return (
    <div className="flex gap-3 flex-wrap mb-4">
      <div className="bg-[#111111] border border-[#1e1e1e] rounded-lg px-4 py-3">
        <div className="text-[10px] uppercase tracking-widest text-[#777] mb-1">
          {showMoney ? "Net P&L" : "Net R"}
        </div>
        <div
          className="text-lg font-bold tabular-nums"
          style={{ color: primaryColor }}
        >
          {showMoney ? formatPnl(stats.netPnl) : formatR(stats.netR)}
        </div>
      </div>

      <div className="bg-[#111111] border border-[#1e1e1e] rounded-lg px-4 py-3">
        <div className="text-[10px] uppercase tracking-widest text-[#777] mb-1">
          Win Rate
        </div>
        <div className="text-lg font-bold tabular-nums text-[#e0e0e0]">
          {stats.winRate !== null ? `${stats.winRate.toFixed(0)}%` : "—"}
        </div>
      </div>

      <div className="bg-[#111111] border border-[#1e1e1e] rounded-lg px-4 py-3">
        <div className="text-[10px] uppercase tracking-widest text-[#777] mb-1">
          Trading Days
        </div>
        <div className="text-lg font-bold tabular-nums text-[#e0e0e0]">
          {stats.tradingDays}
        </div>
      </div>

      <div className="bg-[#111111] border border-[#1e1e1e] rounded-lg px-4 py-3">
        <div className="text-[10px] uppercase tracking-widest text-[#777] mb-1">
          Total Trades
        </div>
        <div className="text-lg font-bold tabular-nums text-[#e0e0e0]">
          {stats.totalTrades}
        </div>
      </div>
    </div>
  );
}
