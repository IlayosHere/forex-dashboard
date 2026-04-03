"use client";

import { useState, useMemo } from "react";

import { StatCard } from "@/components/StatCard";
import { PerformanceTable } from "@/components/PerformanceTable";
import { StatsFilters } from "@/components/StatsFilters";
import { AccountPerformanceTable } from "@/components/AccountPerformanceTable";

import type { InstrumentType, TradeStats, AccountType } from "@/lib/types";

import { useTradeStats } from "@/lib/useTradeStats";
import { useAccounts } from "@/lib/useAccounts";

function fmt(v: number | null | undefined, decimals = 1): string {
  if (v === null || v === undefined) return "--";
  return v.toFixed(decimals);
}

function pnlColor(v: number | null | undefined): string {
  if (v === null || v === undefined || v === 0) return "#777777";
  return v > 0 ? "#26a69a" : "#ef5350";
}

function streakText(streak: number): { text: string; color: string } {
  if (streak === 0) return { text: "--", color: "#777777" };
  if (streak > 0) return { text: `W${streak}`, color: "#26a69a" };
  return { text: `L${Math.abs(streak)}`, color: "#ef5350" };
}

function formatHoldTime(hours: number | null): string {
  if (hours === null) return "--";
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export default function StatisticsPage() {
  const [instrumentType, setInstrumentType] = useState<InstrumentType | "">("");
  const [strategy, setStrategy] = useState("");
  const [accountId, setAccountId] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const { accounts } = useAccounts();

  const apiFilters = useMemo(() => {
    const f: Record<string, string | undefined> = {};
    if (instrumentType) f.instrument_type = instrumentType;
    if (strategy) f.strategy = strategy;
    if (accountId) f.account_id = accountId;
    if (from) f.from = from;
    if (to) f.to = to;
    return f;
  }, [instrumentType, strategy, accountId, from, to]);

  const { stats, loading } = useTradeStats(apiFilters);
  const streak = streakText(stats?.current_streak ?? 0);

  const strategyRows = useMemo(() => buildRows(stats?.by_strategy), [stats?.by_strategy]);
  const symbolRows = useMemo(() => buildRows(stats?.by_symbol), [stats?.by_symbol]);
  const accountRows = useMemo(() => buildAccountRows(stats?.by_account), [stats?.by_account]);

  const dim = loading ? "opacity-50 pointer-events-none" : "";

  return (
    <div className="p-6 max-w-6xl">
      <h1 className="text-lg font-semibold text-[#e0e0e0] mb-4">Statistics</h1>

      <StatsFilters
        instrumentType={instrumentType}
        onInstrumentChange={setInstrumentType}
        strategy={strategy}
        onStrategyChange={setStrategy}
        accountId={accountId}
        onAccountChange={setAccountId}
        accounts={accounts}
        from={from}
        onFromChange={setFrom}
        to={to}
        onToChange={setTo}
      />

      <div className={dim}>
        {/* Overview Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
          <StatCard
            label="Total Trades"
            value={stats ? String(stats.total_trades) : "--"}
            subtitle={stats ? `${stats.open_trades} open / ${stats.closed_trades} closed` : undefined}
          />
          <StatCard
            label="Win Rate"
            value={stats?.win_rate != null ? `${fmt(stats.win_rate)}%` : "--"}
            color={stats?.win_rate != null ? (stats.win_rate >= 50 ? "#26a69a" : "#ef5350") : undefined}
            subtitle={stats ? `${stats.wins}W ${stats.losses}L ${stats.breakevens}BE` : undefined}
          />
          <StatCard
            label="P&L (USD)"
            value={stats ? `${stats.total_pnl_usd >= 0 ? "+" : ""}$${fmt(stats.total_pnl_usd, 2)}` : "--"}
            color={pnlColor(stats?.total_pnl_usd)}
          />
          <StatCard
            label="P&L (Pips)"
            value={stats ? `${stats.total_pnl_pips >= 0 ? "+" : ""}${fmt(stats.total_pnl_pips)}` : "--"}
            color={pnlColor(stats?.total_pnl_pips)}
          />
          <StatCard label="Avg R:R" value={stats?.avg_rr != null ? fmt(stats.avg_rr, 2) : "--"} />
          <StatCard label="Profit Factor" value={stats?.profit_factor != null ? fmt(stats.profit_factor, 2) : "--"} />
          <StatCard label="Streak" value={streak.text} color={streak.color} />
          <StatCard label="Avg Hold Time" value={formatHoldTime(stats?.avg_hold_time_hours ?? null)} />
        </div>

        {/* Breakdowns */}
        <div className="mt-6">
          <PerformanceTable title="Performance by Strategy" rows={strategyRows} />
        </div>
        <div className="mt-4">
          <PerformanceTable title="Performance by Symbol" rows={symbolRows} />
        </div>
        <div className="mt-4">
          <AccountPerformanceTable rows={accountRows} />
        </div>

        {/* Best / Worst */}
        <BestWorstCards best={stats?.best_trade_pnl ?? null} worst={stats?.worst_trade_pnl ?? null} />
      </div>
    </div>
  );
}

/* --- Helpers --- */

type BreakdownMap = TradeStats["by_strategy"] | undefined;

function buildRows(map: BreakdownMap) {
  if (!map) return [];
  return Object.entries(map)
    .map(([name, d]) => ({
      name,
      total: d.total,
      wins: d.wins,
      losses: d.losses,
      winRate: d.win_rate,
      pnl: d.total_pnl_pips,
    }))
    .sort((a, b) => b.total - a.total);
}

function buildAccountRows(map: TradeStats["by_account"] | undefined) {
  if (!map) return [];
  return Object.entries(map)
    .map(([, d]) => ({
      name: d.account_name,
      accountType: d.account_type as AccountType,
      instrumentType: d.instrument_type,
      total: d.total,
      wins: d.wins,
      losses: d.losses,
      winRate: d.win_rate,
      pnlPips: d.total_pnl_pips,
      pnlUsd: d.total_pnl_usd,
    }))
    .sort((a, b) => b.pnlUsd - a.pnlUsd);
}

function BestWorstCards({ best, worst }: { best: number | null; worst: number | null }) {
  if (best === null && worst === null) return null;

  return (
    <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div className="border border-[#2a2a2a] rounded-lg px-4 py-4" style={{ backgroundColor: "#161616" }}>
        <div className="text-xs text-[#777777] uppercase tracking-wide mb-1">Best Trade</div>
        <div
          className="text-xl font-bold"
          style={{ color: best !== null && best > 0 ? "#26a69a" : "#777777", fontVariantNumeric: "tabular-nums" }}
        >
          {best !== null ? `${best >= 0 ? "+" : ""}$${fmt(best, 2)}` : "--"}
        </div>
      </div>
      <div className="border border-[#2a2a2a] rounded-lg px-4 py-4" style={{ backgroundColor: "#161616" }}>
        <div className="text-xs text-[#777777] uppercase tracking-wide mb-1">Worst Trade</div>
        <div
          className="text-xl font-bold"
          style={{ color: worst !== null && worst < 0 ? "#ef5350" : "#777777", fontVariantNumeric: "tabular-nums" }}
        >
          {worst !== null ? `${worst >= 0 ? "+" : ""}$${fmt(worst, 2)}` : "--"}
        </div>
      </div>
    </div>
  );
}
