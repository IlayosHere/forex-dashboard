"use client";

import { useMemo, useState } from "react";

import type { IctBucketStats, TimeEdgeStats } from "@/lib/ictTypes";

import {
  expectancyColor,
  formatExpectancy,
  formatWinRate,
  PHASE_LABELS,
  PHASE_ORDER,
} from "@/lib/timeEdgeHelpers";

type ViewKey = "phase" | "slice" | "macro";

const VIEWS: { key: ViewKey; label: string }[] = [
  { key: "phase", label: "NY phase" },
  { key: "slice", label: "15-min slice" },
  { key: "macro", label: "ICT macro" },
];

// 15-min slices always shown (even when empty) across the core window; others only if traded
const CORE_SLICE_FIRST = "09:30";
const CORE_SLICE_LAST = "10:45";
const BAR_FULL_R = 1.5; // |expectancy| that fills half of the diverging bar

interface TimePhaseBarsProps {
  timeEdge: TimeEdgeStats;
  loading: boolean;
}

interface BarRow {
  key: string;
  label: string;
  stats: IctBucketStats;
}

function buildRows(timeEdge: TimeEdgeStats, view: ViewKey): BarRow[] {
  if (view === "phase") {
    return PHASE_ORDER.map((key) => ({
      key,
      label: PHASE_LABELS[key],
      stats: timeEdge.by_ny_phase[key],
    })).filter((r) => r.stats && (r.key !== "other" || r.stats.total > 0));
  }
  if (view === "slice") {
    return Object.entries(timeEdge.by_time_slice)
      .filter(([key, stats]) => stats.total > 0 || (key >= CORE_SLICE_FIRST && key <= CORE_SLICE_LAST))
      .map(([key, stats]) => ({ key, label: key, stats }));
  }
  return Object.entries(timeEdge.by_macro)
    .filter(([key, stats]) => stats.total > 0 || (key !== "other" && key !== "outside"))
    .map(([key, stats]) => ({ key, label: key === "outside" ? "Outside macros" : key, stats }));
}

function ExpectancyBar({ value }: { value: number | null }) {
  const width = value === null ? 0 : Math.min(Math.abs(value) / BAR_FULL_R, 1) * 50;
  const positive = (value ?? 0) >= 0;
  return (
    <div className="relative h-2 flex-1 rounded-full bg-[#1e1e1e]">
      <div className="absolute inset-y-0 left-1/2 w-px bg-[#333]" />
      <div
        className="absolute inset-y-0 rounded-full"
        style={{
          width: `${width}%`,
          left: positive ? "50%" : `${50 - width}%`,
          backgroundColor: expectancyColor(value),
        }}
      />
    </div>
  );
}

function BarRowView({ row, minSample }: { row: BarRow; minSample: number }) {
  const { stats } = row;
  const thin = stats.total > 0 && stats.total < minSample;
  const dim = stats.total === 0 ? "opacity-30" : thin ? "opacity-60" : "";
  return (
    <div className={`flex items-center gap-3 py-1.5 border-b border-b-[#1a1a1a] ${dim}`}>
      <span className="text-xs text-text-primary w-40 shrink-0">{row.label}</span>
      <ExpectancyBar value={stats.expectancy_r} />
      <span className="text-xs w-16 text-right tabular-nums" style={{ color: expectancyColor(stats.expectancy_r) }}>
        {formatExpectancy(stats.expectancy_r)}
      </span>
      <span className="text-xs text-text-muted w-10 text-right tabular-nums">{formatWinRate(stats.win_rate)}</span>
      <span className="text-xs text-text-muted w-12 text-right tabular-nums">
        {stats.total}
        {thin ? "*" : ""}
      </span>
    </div>
  );
}

export function TimePhaseBars({ timeEdge, loading }: TimePhaseBarsProps) {
  const [view, setView] = useState<ViewKey>("phase");
  const rows = useMemo(() => buildRows(timeEdge, view), [timeEdge, view]);
  const dim = loading ? "opacity-50" : "";

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <p className="text-xs uppercase tracking-widest text-text-muted mb-4">Where in the session you win</p>
      <div className="flex gap-0 border-b border-border mb-3">
        {VIEWS.map((v) => (
          <button
            key={v.key}
            type="button"
            onClick={() => setView(v.key)}
            className={`px-4 py-2 text-xs font-medium -mb-px ${
              view === v.key
                ? "text-bull border-b-2 border-bull"
                : "text-text-muted hover:text-text-primary border-b-2 border-transparent"
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>
      <div className="flex items-center gap-3 pb-1 text-xs text-text-dim">
        <span className="w-40 shrink-0">Window (ET)</span>
        <span className="flex-1">Expectancy</span>
        <span className="w-16 text-right">Exp. R</span>
        <span className="w-10 text-right">Win</span>
        <span className="w-12 text-right">Trades</span>
      </div>
      {rows.map((row) => (
        <BarRowView key={row.key} row={row} minSample={timeEdge.min_sample} />
      ))}
      <p className="text-[10px] text-text-dim mt-2">
        * fewer than {timeEdge.min_sample} trades — treat as noise. Times are the entry time in New York.
      </p>
    </div>
  );
}
