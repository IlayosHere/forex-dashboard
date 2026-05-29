"use client";

import { useMemo } from "react";

import type { DailySummaryPoint } from "@/lib/types";

import { fmt } from "@/lib/format";

interface MonthlyBarsProps {
  data: DailySummaryPoint[];
  loading: boolean;
  isBacktest?: boolean;
  showMoney?: boolean;
}

interface MonthBucket {
  month: string;
  pnl: number;
}

function aggregateMonthly(data: DailySummaryPoint[], useR: boolean): MonthBucket[] {
  const map = new Map<string, number>();
  for (const d of data) {
    const key = d.date.slice(0, 7);
    map.set(key, (map.get(key) ?? 0) + (useR ? (d.pnl_r ?? 0) : d.pnl_usd));
  }
  return Array.from(map.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, pnl]) => {
      const date = new Date(key + "-01");
      return {
        month: date.toLocaleDateString("en-US", { month: "short", year: "2-digit" }),
        pnl,
      };
    });
}

export function MonthlyBars({ data, loading, isBacktest = false, showMoney = true }: MonthlyBarsProps) {
  const monthly = useMemo(() => aggregateMonthly(data, !showMoney), [data, showMoney]);
  const dim = loading ? "opacity-50" : "";

  const maxAbs = monthly.reduce((acc, m) => Math.max(acc, Math.abs(m.pnl)), 0);

  const title = showMoney
    ? (isBacktest ? "Monthly P&L (notional)" : "Monthly P&L")
    : "Monthly R";

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">
        {title}
      </h3>

      {monthly.length === 0 ? (
        <p className="text-text-dim text-sm py-4 text-center">No data</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {monthly.map((m) => {
            const isPositive = m.pnl >= 0;
            const fillPct = maxAbs > 0 ? (Math.abs(m.pnl) / maxAbs) * 100 : 0;
            const barColor = (showMoney && isBacktest)
              ? (isPositive ? "bg-bull/40" : "bg-bear/40")
              : (isPositive ? "bg-bull" : "bg-bear");
            const textColor = (showMoney && isBacktest)
              ? "text-text-muted"
              : (isPositive ? "text-bull" : "text-bear");
            return (
              <div key={m.month} className="flex items-center gap-2 min-w-0">
                <span className="text-xs text-text-muted w-12 shrink-0 tabular-nums">{m.month}</span>
                <div className="flex-1 h-4 flex items-center min-w-0 overflow-hidden rounded-sm">
                  <div
                    className={`h-2 rounded-sm ${barColor}`}
                    style={{ width: `${fillPct}%` }}
                    aria-hidden="true"
                  />
                </div>
                <span className={`text-xs tabular-nums shrink-0 w-20 text-right ${textColor}`}>
                  {isPositive ? "+" : ""}
                  {showMoney && !isBacktest ? "$" : ""}
                  {fmt(m.pnl, showMoney ? 0 : 2)}
                  {!showMoney ? "R" : ""}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
