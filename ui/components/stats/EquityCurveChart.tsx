"use client";

import { useMemo } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

import type { EquityCurvePoint } from "@/lib/types";

import { fmt } from "@/lib/format";

interface EquityCurveChartProps {
  data: EquityCurvePoint[];
  loading: boolean;
  isBacktest?: boolean;
  showMoney?: boolean;
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

function CustomTooltip({
  active,
  payload,
  isBacktest,
  showMoney = true,
}: {
  active?: boolean;
  payload?: { payload: ChartPoint }[];
  isBacktest?: boolean;
  showMoney?: boolean;
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  const prefix = !showMoney ? "" : (isBacktest ? "" : "$");
  const suffix = !showMoney ? "R" : (isBacktest ? " (notional)" : "");
  return (
    <div className="bg-surface-raised border border-border rounded px-3 py-2 text-xs">
      <p className="text-text-primary mb-1">{d.label}</p>
      <p style={{ color: d.pnl >= 0 ? "#26a69a" : "#ef5350" }}>
        Trade: {d.pnl >= 0 ? "+" : ""}{prefix}{fmt(d.pnl, 2)}{suffix}
      </p>
      <p style={{ color: d.cumulative >= 0 ? "#26a69a" : "#ef5350" }}>
        Cumulative: {d.cumulative >= 0 ? "+" : ""}{prefix}{fmt(d.cumulative, 2)}{suffix}
      </p>
    </div>
  );
}

export function EquityCurveChart({
  data,
  loading,
  isBacktest = false,
  showMoney = true,
}: EquityCurveChartProps) {
  const chartData = useMemo<ChartPoint[]>(() =>
    data.map((p) => ({
      date: formatDate(p.close_time ?? p.date),
      cumulative: showMoney ? p.cumulative_pnl_usd : (p.cumulative_r ?? 0),
      pnl: showMoney ? p.pnl_usd : (p.pnl_r ?? 0),
      label: p.close_time
        ? new Date(p.close_time).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
        : p.date ?? "",
    })),
  [data, showMoney]);

  const isPositive = chartData.length > 0 && chartData[chartData.length - 1].cumulative >= 0;
  const gradientColor = isPositive ? "#26a69a" : "#ef5350";
  const dim = loading ? "opacity-50" : "";

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      {showMoney && isBacktest && (
        <p className="text-[10px] uppercase tracking-widest text-text-muted mb-2">
          Notional P&amp;L — lot size is arbitrary in backtest
        </p>
      )}
      <ResponsiveContainer width="100%" height={180}>
        <AreaChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: 8 }}>
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={gradientColor} stopOpacity={(showMoney && isBacktest) ? 0.15 : 0.3} />
              <stop offset="100%" stopColor={gradientColor} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="0" stroke="#2a2a2a" strokeOpacity={0.6} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fontFamily: "monospace" }}
            axisLine={{ stroke: "#2a2a2a" }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            width={(showMoney && isBacktest) ? 60 : 48}
            tick={{ fontSize: 11, fontFamily: "monospace", fill: (showMoney && isBacktest) ? "#555" : undefined }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => showMoney ? (isBacktest ? `${v}` : `$${v}`) : `${v}R`}
            label={(showMoney && isBacktest) ? {
              value: "notional",
              angle: -90,
              position: "insideLeft",
              offset: 12,
              style: { fontSize: 9, fill: "#444", textAnchor: "middle" },
            } : undefined}
          />
          <ReferenceLine y={0} stroke="#2a2a2a" strokeDasharray="3 3" />
          <Tooltip
            content={<CustomTooltip isBacktest={isBacktest} showMoney={showMoney} />}
            contentStyle={{ background: "#1a1a1a", border: "1px solid #2a2a2a", borderRadius: "6px", fontSize: "12px" }}
          />
          <Area
            type="monotone"
            dataKey="cumulative"
            stroke={(showMoney && isBacktest) ? "#888" : gradientColor}
            strokeWidth={1.5}
            fill="url(#equityGradient)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
