"use client";

import { useMemo } from "react";
import {
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Line,
  ComposedChart,
} from "recharts";

import type { BreakdownEntry } from "@/lib/types";

import { fmt } from "@/lib/format";

interface AssessmentAnalysisProps {
  byConfidence: Record<string, BreakdownEntry> | undefined;
  byRating: Record<string, BreakdownEntry> | undefined;
  loading: boolean;
}

interface LevelData {
  level: string;
  winRate: number;
  avgPnl: number;
  total: number;
}

function buildLevels(map: Record<string, BreakdownEntry> | undefined): LevelData[] {
  const levels: LevelData[] = [];
  for (let i = 1; i <= 5; i++) {
    const key = String(i);
    const entry = map?.[key];
    levels.push({
      level: key,
      winRate: entry?.win_rate ?? 0,
      avgPnl: entry?.avg_pnl_usd ?? 0,
      total: entry?.total ?? 0,
    });
  }
  return levels;
}

function LevelTooltip({ active, payload }: { active?: boolean; payload?: { payload: LevelData }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-surface-raised border border-border rounded px-3 py-2 text-xs">
      <p className="text-text-primary">Level {d.level}</p>
      <p className="text-text-muted">{d.total} trades</p>
      <p className="text-text-muted">Win Rate: {fmt(d.winRate)}%</p>
      <p style={{ color: d.avgPnl >= 0 ? "#26a69a" : "#ef5350" }}>
        Avg P&L: {d.avgPnl >= 0 ? "+" : ""}${fmt(d.avgPnl, 2)}
      </p>
    </div>
  );
}

function LevelChart({ title, data }: { title: string; data: LevelData[] }) {
  const hasData = data.some((d) => d.total > 0);

  return (
    <div className="flex-1 min-w-0">
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">{title}</h3>
      {!hasData ? (
        <p className="text-text-dim text-sm py-8 text-center">No data</p>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <ComposedChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
            <XAxis
              dataKey="level"
              tick={{ fill: "#777777", fontSize: 11 }}
              axisLine={{ stroke: "#2a2a2a" }}
              tickLine={false}
            />
            <YAxis
              yAxisId="left"
              tick={{ fill: "#777777", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `${v}%`}
              domain={[0, 100]}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fill: "#777777", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `$${v}`}
            />
            <Tooltip content={<LevelTooltip />} />
            <Bar yAxisId="left" dataKey="winRate" fill="#26a69a" opacity={0.6} radius={[2, 2, 0, 0]} />
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="avgPnl"
              stroke="#e6a800"
              strokeWidth={2}
              dot={{ fill: "#e6a800", r: 4 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export function AssessmentAnalysis({ byConfidence, byRating, loading }: AssessmentAnalysisProps) {
  const confidenceData = useMemo(() => buildLevels(byConfidence), [byConfidence]);
  const ratingData = useMemo(() => buildLevels(byRating), [byRating]);
  const dim = loading ? "opacity-50" : "";

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <div className="flex gap-6">
        <LevelChart title="By Confidence Level" data={confidenceData} />
        <LevelChart title="By Rating Level" data={ratingData} />
      </div>
      <div className="flex items-center gap-4 mt-3 text-[10px] text-text-dim">
        <span className="flex items-center gap-1">
          <span className="w-3 h-2 rounded-sm bg-bull opacity-60 inline-block" /> Win Rate
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-0.5 bg-accent-gold inline-block" /> Avg P&L
        </span>
      </div>
    </div>
  );
}
