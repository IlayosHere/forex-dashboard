"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

import type { RollingExpectancyPoint } from "@/lib/types";

import { COLOR_BULL, COLOR_BEAR } from "@/lib/statsHelpers";
import { fmt } from "@/lib/format";

interface RollingExpectancyChartProps {
  data: RollingExpectancyPoint[];
  loading: boolean;
}

const COLOR_AMBER = "#f59e0b";

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: RollingExpectancyPoint }[];
}) {
  if (!active || !payload?.length) return null;
  const pt = payload[0].payload;
  const val = pt.rolling_expectancy_r;
  const sign = val >= 0 ? "+" : "";
  return (
    <div className="bg-card border border-border rounded px-3 py-2 text-xs">
      <p className="text-text-muted">Trade #{pt.index}</p>
      <p className="text-text-primary font-semibold">
        {sign}{fmt(val, 2)}R
      </p>
    </div>
  );
}

function tickFormatter(v: number): string {
  return fmt(v, 2);
}

export function RollingExpectancyChart({ data, loading }: RollingExpectancyChartProps) {
  if (loading) {
    return (
      <div className="bg-card border border-border rounded-lg p-4 opacity-50">
        <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">
          Rolling Expectancy (30-trade)
        </h3>
        <div className="h-[200px]" />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">
          Rolling Expectancy (30-trade)
        </h3>
        <div className="h-[200px] flex items-center justify-center">
          <p className="text-text-muted text-sm text-center">
            Need 30 closed trades for rolling expectancy
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">
        Rolling Expectancy (30-trade)
      </h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <XAxis
            dataKey="index"
            tick={false}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={tickFormatter}
            width={45}
            tick={{ fontSize: 10, fill: "#777777" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke={COLOR_AMBER} strokeDasharray="4 2" />
          <Line
            type="monotone"
            dataKey="rolling_expectancy_r"
            stroke={COLOR_BULL}
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
