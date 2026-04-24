"use client";

import { useMemo } from "react";

import type { DailySummaryPoint } from "@/lib/types";

import { fmt } from "@/lib/format";

interface MonthlyBarsProps {
  data: DailySummaryPoint[];
  loading: boolean;
}

interface MonthBucket {
  month: string;
  pnl: number;
}

function aggregateMonthly(data: DailySummaryPoint[]): MonthBucket[] {
  const map = new Map<string, number>();
  for (const d of data) {
    const key = d.date.slice(0, 7);
    map.set(key, (map.get(key) ?? 0) + d.pnl_usd);
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

export function MonthlyBars({ data, loading }: MonthlyBarsProps) {
  const monthly = useMemo(() => aggregateMonthly(data), [data]);
  const dim = loading ? "opacity-50" : "";

  const maxAbs = monthly.reduce((acc, m) => Math.max(acc, Math.abs(m.pnl)), 0);

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Monthly P&amp;L</h3>

      {monthly.length === 0 ? (
        <p className="text-text-dim text-sm py-4 text-center">No data</p>
      ) : (
        <div className="flex flex-col gap-1.5">
          {monthly.map((m) => {
            const isPositive = m.pnl >= 0;
            const fillPct = maxAbs > 0 ? (Math.abs(m.pnl) / maxAbs) * 100 : 0;
            return (
              <div key={m.month} className="flex items-center gap-2 min-w-0">
                <span className="text-xs text-text-muted w-12 shrink-0 tabular-nums">{m.month}</span>
                <div className="flex-1 h-4 flex items-center min-w-0 overflow-hidden rounded-sm">
                  <div
                    className={`h-2 rounded-sm ${isPositive ? "bg-bull" : "bg-bear"}`}
                    style={{ width: `${fillPct}%` }}
                    aria-hidden="true"
                  />
                </div>
                <span className={`text-xs tabular-nums shrink-0 w-16 text-right ${isPositive ? "text-bull" : "text-bear"}`}>
                  {isPositive ? "+" : ""}${fmt(m.pnl, 0)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
