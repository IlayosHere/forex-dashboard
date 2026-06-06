"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

import type { StatsFiltersParam } from "@/lib/api";
import type { RollingPfPoint } from "@/lib/types";

import { useRollingPf } from "@/lib/useRollingPf";
import { COLOR_BULL } from "@/lib/statsHelpers";

interface RollingProfitFactorProps {
  filters: StatsFiltersParam;
}

interface ChartPoint {
  index: number;
  value: number | undefined;
}

function toChartPoints(data: RollingPfPoint[]): ChartPoint[] {
  return data.map((pt) => ({
    index: pt.index,
    value: pt.profit_factor ?? undefined,
  }));
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: ChartPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const pt = payload[0].payload;
  return (
    <div className="bg-card border border-border rounded px-3 py-2 text-xs">
      <p className="text-text-muted">Trade #{pt.index}</p>
      <p className="text-text-primary font-semibold">
        {pt.value != null ? `PF: ${pt.value.toFixed(2)}` : "—"}
      </p>
    </div>
  );
}

export function RollingProfitFactor({ filters }: RollingProfitFactorProps) {
  const { data, loading, error } = useRollingPf(filters);

  if (loading) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Rolling Profit Factor</h3>
        <div className="h-48 flex items-center justify-center">
          <p className="text-text-muted text-xs">Loading…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Rolling Profit Factor</h3>
        <p className="text-bear text-xs text-center py-8">{error}</p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Rolling Profit Factor</h3>
        <p className="text-muted-foreground text-sm text-center py-8">
          Need ≥20 trades for rolling profit factor
        </p>
      </div>
    );
  }

  const chartPoints = toChartPoints(data);

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Rolling Profit Factor</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartPoints} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" vertical={false} />
          <XAxis
            dataKey="index"
            tick={{ fontSize: 10, fill: "#777777" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "#777777" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine
            y={1}
            stroke="#777777"
            strokeDasharray="4 2"
            label={{ value: "Break-even", fill: "#777777", fontSize: 10 }}
          />
          <ReferenceLine
            y={1.5}
            stroke={COLOR_BULL}
            strokeDasharray="4 2"
            label={{ value: "1.5R target", fill: COLOR_BULL, fontSize: 10 }}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={COLOR_BULL}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
