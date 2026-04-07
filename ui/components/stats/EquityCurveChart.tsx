"use client";

import { useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

import type { EquityCurvePoint, TradeStats } from "@/lib/types";

import { fmt } from "@/lib/format";

interface EquityCurveChartProps {
  data: EquityCurvePoint[];
  stats: TradeStats | null;
  loading: boolean;
}

interface ChartPoint {
  date: string;
  cumulative: number;
  pnl: number;
  label: string;
}

function formatDate(raw: string | null): string {
  if (!raw) return "";
  const d = new Date(raw);
  return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: ChartPoint }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-surface-raised border border-border rounded px-3 py-2 text-xs">
      <p className="text-text-primary mb-1">{d.label}</p>
      <p style={{ color: d.pnl >= 0 ? "#26a69a" : "#ef5350" }}>
        Trade: {d.pnl >= 0 ? "+" : ""}${fmt(d.pnl, 2)}
      </p>
      <p style={{ color: d.cumulative >= 0 ? "#26a69a" : "#ef5350" }}>
        Cumulative: {d.cumulative >= 0 ? "+" : ""}${fmt(d.cumulative, 2)}
      </p>
    </div>
  );
}

export function EquityCurveChart({ data, stats, loading }: EquityCurveChartProps) {
  const chartData = useMemo<ChartPoint[]>(() =>
    data.map((p) => ({
      date: formatDate(p.close_time ?? p.date),
      cumulative: p.cumulative_pnl_usd,
      pnl: p.pnl_usd,
      label: p.close_time
        ? new Date(p.close_time).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
        : p.date ?? "",
    })),
  [data]);

  const isPositive = chartData.length > 0 && chartData[chartData.length - 1].cumulative >= 0;
  const gradientColor = isPositive ? "#26a69a" : "#ef5350";
  const dim = loading ? "opacity-50" : "";

  return (
    <div className={`relative bg-card border border-border rounded-lg p-4 ${dim}`}>
      {/* KPI overlay */}
      <div className="absolute top-4 left-4 z-10 flex gap-6">
        <KPI label="Total P&L" value={stats ? `${stats.total_pnl_usd >= 0 ? "+" : ""}$${fmt(stats.total_pnl_usd, 2)}` : "--"} color={stats ? (stats.total_pnl_usd >= 0 ? "#26a69a" : "#ef5350") : "#777777"} />
        <KPI label="Win Rate" value={stats?.win_rate != null ? `${fmt(stats.win_rate)}%` : "--"} />
        <KPI label="Profit Factor" value={stats?.profit_factor != null ? fmt(stats.profit_factor, 2) : "--"} />
        <KPI label="Expectancy" value={stats?.expectancy_usd != null ? `$${fmt(stats.expectancy_usd, 2)}` : "--"} color={stats?.expectancy_usd != null ? (stats.expectancy_usd >= 0 ? "#26a69a" : "#ef5350") : "#777777"} />
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <AreaChart data={chartData} margin={{ top: 50, right: 8, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={gradientColor} stopOpacity={0.3} />
              <stop offset="100%" stopColor={gradientColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis
            dataKey="date"
            tick={{ fill: "#777777", fontSize: 11 }}
            axisLine={{ stroke: "#2a2a2a" }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: "#777777", fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => `$${v}`}
          />
          <ReferenceLine y={0} stroke="#2a2a2a" strokeDasharray="3 3" />
          <Tooltip content={<CustomTooltip />} />
          <Area
            type="monotone"
            dataKey="cumulative"
            stroke={gradientColor}
            strokeWidth={2}
            fill="url(#equityGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function KPI({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wide text-text-muted">{label}</div>
      <div className="text-sm font-bold price" style={{ color: color ?? "#e0e0e0" }}>{value}</div>
    </div>
  );
}
