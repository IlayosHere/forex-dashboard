"use client";

import { useState, useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { useRouter } from "next/navigation";

import type { TradeStats } from "@/lib/types";

import { fmt } from "@/lib/format";

interface PerformanceBreakdownsProps {
  stats: TradeStats | null;
  loading: boolean;
}

type TabKey = "strategy" | "symbol" | "day" | "session";

interface RowData {
  name: string;
  total: number;
  winRate: number | null;
  pnl: number;
  filterKey: string;
  filterValue: string;
}

const TABS: { key: TabKey; label: string }[] = [
  { key: "strategy", label: "Strategy" },
  { key: "symbol", label: "Symbol" },
  { key: "day", label: "Day of Week" },
  { key: "session", label: "Session" },
];

function buildRows(stats: TradeStats | null, tab: TabKey): RowData[] {
  if (!stats) return [];

  const source = tab === "strategy" ? stats.by_strategy
    : tab === "symbol" ? stats.by_symbol
    : tab === "day" ? stats.by_day_of_week
    : stats.by_session;

  if (!source) return [];

  return Object.entries(source)
    .map(([key, d]) => ({
      name: "name" in d ? (d as { name: string }).name : key,
      total: d.total,
      winRate: d.win_rate,
      pnl: d.total_pnl_usd ?? d.total_pnl_pips,
      filterKey: tab === "strategy" ? "strategy" : tab === "symbol" ? "symbol" : "",
      filterValue: key,
    }))
    .sort((a, b) => b.pnl - a.pnl);
}

function RowTooltip({ active, payload }: { active?: boolean; payload?: { payload: RowData }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-surface-raised border border-border rounded px-3 py-2 text-xs">
      <p className="text-text-primary font-medium">{d.name}</p>
      <p className="text-text-muted">{d.total} trades</p>
      <p className="text-text-muted">WR: {d.winRate != null ? `${fmt(d.winRate)}%` : "--"}</p>
      <p style={{ color: d.pnl >= 0 ? "#26a69a" : "#ef5350" }}>
        P&L: {d.pnl >= 0 ? "+" : ""}${fmt(d.pnl, 2)}
      </p>
    </div>
  );
}

export function PerformanceBreakdowns({ stats, loading }: PerformanceBreakdownsProps) {
  const [tab, setTab] = useState<TabKey>("strategy");
  const router = useRouter();
  const rows = useMemo(() => buildRows(stats, tab), [stats, tab]);
  const dim = loading ? "opacity-50" : "";

  function handleClick(row: RowData) {
    if (!row.filterKey) return;
    const params = new URLSearchParams();
    params.set(row.filterKey, row.filterValue);
    router.push(`/journal?${params.toString()}`);
  }

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      {/* Tabs */}
      <div className="flex gap-0 mb-4 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-xs font-medium -mb-px ${
              tab === t.key
                ? "text-bull border-b-2 border-bull"
                : "text-text-muted hover:text-text-primary border-b-2 border-transparent"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <p className="text-text-dim text-sm py-8 text-center">No data available</p>
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(rows.length * 36 + 20, 120)}>
          <BarChart data={rows} layout="vertical" margin={{ top: 0, right: 60, bottom: 0, left: 80 }}>
            <XAxis
              type="number"
              tick={{ fill: "#777777", fontSize: 10 }}
              axisLine={{ stroke: "#2a2a2a" }}
              tickLine={false}
              tickFormatter={(v: number) => `$${v}`}
            />
            <YAxis
              type="category"
              dataKey="name"
              tick={{ fill: "#e0e0e0", fontSize: 11, cursor: "pointer" }}
              axisLine={false}
              tickLine={false}
              width={76}
            />
            <Tooltip content={<RowTooltip />} />
            <Bar
              dataKey="pnl"
              radius={[0, 4, 4, 0]}
              onClick={(_: unknown, index: number) => handleClick(rows[index])}
              cursor="pointer"
            >
              {rows.map((entry) => (
                <Cell key={entry.name} fill={entry.pnl >= 0 ? "#26a69a" : "#ef5350"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
