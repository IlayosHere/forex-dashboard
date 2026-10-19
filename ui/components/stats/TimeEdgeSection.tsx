"use client";

import { TimeCrossMatrix } from "@/components/stats/TimeCrossMatrix";
import { TimePhaseBars } from "@/components/stats/TimePhaseBars";

import type { TimeEdgeStats, TimeInsight } from "@/lib/ictTypes";

import {
  expectancyColor,
  formatExpectancy,
  formatWinRate,
  PHASE_LABELS,
  rowLabel,
} from "@/lib/timeEdgeHelpers";

interface TimeEdgeSectionProps {
  timeEdge: TimeEdgeStats | null | undefined;
  loading: boolean;
}

function InsightCard({ insight }: { insight: TimeInsight }) {
  const strength = insight.kind === "strength";
  const subject = insight.dimension === "All trades" ? "Any trade" : rowLabel("", insight.row);
  return (
    <div className={`rounded-lg border p-3 ${strength ? "border-bull/30 bg-bull/5" : "border-bear/30 bg-bear/5"}`}>
      <p className="text-[10px] uppercase tracking-widest text-text-muted">
        {strength ? "Strength" : "Leak"} · {insight.dimension}
      </p>
      <p className="text-sm text-text-primary mt-1">
        {subject} <span className="text-text-muted">in</span> {PHASE_LABELS[insight.phase] ?? insight.phase}
      </p>
      <p className="text-xs mt-1 tabular-nums" style={{ color: expectancyColor(insight.stats.expectancy_r) }}>
        {formatExpectancy(insight.stats.expectancy_r)}
        <span className="text-text-muted">
          {" "}· {formatWinRate(insight.stats.win_rate)} win · {insight.stats.total} trades
        </span>
      </p>
    </div>
  );
}

export function TimeEdgeSection({ timeEdge, loading }: TimeEdgeSectionProps) {
  if (!timeEdge) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <p className="text-text-dim text-sm text-center py-4">
          {loading ? "Loading time-of-day edge…" : "No time-of-day data yet."}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {timeEdge.insights.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {timeEdge.insights.map((i) => (
            <InsightCard key={`${i.kind}-${i.dimension}-${i.row}-${i.phase}`} insight={i} />
          ))}
        </div>
      )}
      <TimePhaseBars timeEdge={timeEdge} loading={loading} />
      <TimeCrossMatrix timeEdge={timeEdge} loading={loading} />
    </div>
  );
}
