"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
} from "recharts";

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

function MonthlyTooltip({ active, payload }: { active?: boolean; payload?: { payload: MonthBucket }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-surface-raised border border-border rounded px-3 py-2 text-xs">
      <p className="text-text-primary">{d.month}</p>
      <p style={{ color: d.pnl >= 0 ? "#26a69a" : "#ef5350" }}>
        {d.pnl >= 0 ? "+" : ""}${fmt(d.pnl, 2)}
      </p>
    </div>
  );
}

export function MonthlyBars({ data, loading }: MonthlyBarsProps) {
  const monthly = useMemo(() => aggregateMonthly(data), [data]);
  const dim = loading ? "opacity-50" : "";

  const best = monthly.reduce<MonthBucket | null>((acc, m) => (!acc || m.pnl > acc.pnl ? m : acc), null);
  const worst = monthly.reduce<MonthBucket | null>((acc, m) => (!acc || m.pnl < acc.pnl ? m : acc), null);

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Monthly P&L</h3>

      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={monthly} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
          <XAxis
            dataKey="month"
            tick={{ fill: "#777777", fontSize: 10 }}
            axisLine={{ stroke: "#2a2a2a" }}
            tickLine={false}
          />
          <YAxis
            tick={{ fill: "#777777", fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `$${v}`}
          />
          <ReferenceLine y={0} stroke="#2a2a2a" />
          <Tooltip content={<MonthlyTooltip />} />
          <Bar dataKey="pnl" radius={[2, 2, 0, 0]}>
            {monthly.map((entry) => (
              <Cell key={entry.month} fill={entry.pnl >= 0 ? "#26a69a" : "#ef5350"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Best / Worst labels */}
      <div className="flex justify-between mt-2 text-[10px]">
        <div>
          <span className="text-text-dim">Best: </span>
          {best && (
            <span className="text-bull">{best.month} (+${fmt(best.pnl, 2)})</span>
          )}
        </div>
        <div>
          <span className="text-text-dim">Worst: </span>
          {worst && (
            <span className="text-bear">{worst.month} (${fmt(worst.pnl, 2)})</span>
          )}
        </div>
      </div>
    </div>
  );
}
