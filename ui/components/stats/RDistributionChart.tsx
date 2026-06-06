"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";

import type { RDistributionBin } from "@/lib/types";

import { COLOR_BULL, COLOR_BEAR } from "@/lib/statsHelpers";

interface RDistributionChartProps {
  distribution: RDistributionBin[];
}

const NEGATIVE_LABELS = new Set(["<-3R", "-3 to -2R", "-2 to -1R", "-1 to 0R"]);

function binColor(label: string): string {
  return NEGATIVE_LABELS.has(label) ? COLOR_BEAR : COLOR_BULL;
}

function isEmpty(distribution: RDistributionBin[]): boolean {
  return distribution.length === 0 || distribution.every((b) => b.count === 0);
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: RDistributionBin }[];
}) {
  if (!active || !payload?.length) return null;
  const bin = payload[0].payload;
  return (
    <div className="bg-card border border-border rounded px-3 py-2 text-xs">
      <p className="text-text-primary font-semibold">{bin.bucket_label}</p>
      <p className="text-text-muted">{bin.count} trade{bin.count !== 1 ? "s" : ""}</p>
      <p className="text-text-muted">{bin.pct.toFixed(1)}%</p>
    </div>
  );
}

export function RDistributionChart({ distribution }: RDistributionChartProps) {
  if (isEmpty(distribution)) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">R Distribution</h3>
        <p className="text-muted-foreground text-sm text-center py-8">No closed trades yet</p>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">R Distribution</h3>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={distribution} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a2a" vertical={false} />
          <XAxis
            dataKey="bucket_label"
            tick={{ fontSize: 10, fill: "#777777" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v: number) => `${v}%`}
            tick={{ fontSize: 10, fill: "#777777" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="pct" radius={[2, 2, 0, 0]}>
            {distribution.map((bin) => (
              <Cell key={bin.bucket_label} fill={binColor(bin.bucket_label)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
