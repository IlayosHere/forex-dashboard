"use client";

import type { DrawdownStats } from "@/lib/types";

import { fmt } from "@/lib/format";
import { COLOR_BULL, COLOR_BEAR } from "@/lib/statsHelpers";

interface DrawdownPanelProps {
  drawdown: DrawdownStats | null | undefined;
}

interface MetricRowProps {
  label: string;
  value: string;
  color?: string;
  sub?: string;
}

function MetricRow({ label, value, color, sub }: MetricRowProps) {
  return (
    <div className="flex justify-between items-start py-1.5">
      <span className="text-xs text-text-muted">{label}</span>
      <span className="text-right">
        <span
          className="text-sm font-semibold price block tabular-nums"
          style={{ color: color ?? "#e0e0e0" }}
        >
          {value}
        </span>
        {sub && <span className="text-[10px] text-text-muted">{sub}</span>}
      </span>
    </div>
  );
}

const COLOR_AMBER = "#f59e0b";

function recoveryFactorColor(rf: number | null): string {
  if (rf == null) return "#777777";
  if (rf >= 3) return COLOR_BULL;
  if (rf >= 1) return COLOR_AMBER;
  return COLOR_BEAR;
}

export function DrawdownPanel({ drawdown }: DrawdownPanelProps) {
  if (drawdown == null) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Drawdown</h3>
        <div className="divide-y divide-border">
          <MetricRow label="Max Drawdown (R)" value="—" />
          <MetricRow label="Max Losing Streak" value="—" />
          <MetricRow label="Expected Max Streak" value="—" />
          <MetricRow label="Recovery Factor" value="—" />
        </div>
      </div>
    );
  }

  const rf = drawdown.recovery_factor;
  const expectedStreak = drawdown.expected_max_streak;

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Drawdown</h3>
      <div className="divide-y divide-border">
        <MetricRow
          label="Max Drawdown (R)"
          value={`${fmt(Math.abs(drawdown.max_drawdown_r), 2)}R`}
          color={COLOR_BEAR}
        />
        <MetricRow
          label="Max Losing Streak"
          value={String(drawdown.max_losing_streak)}
          sub="consecutive losses"
        />
        <MetricRow
          label="Expected Max Streak"
          value={expectedStreak != null ? String(expectedStreak) : "—"}
          sub={expectedStreak != null ? "statistical estimate" : undefined}
        />
        <MetricRow
          label="Recovery Factor"
          value={rf != null ? fmt(rf, 2) : "—"}
          color={recoveryFactorColor(rf)}
          sub={rf != null ? (rf >= 3 ? "strong" : rf >= 1 ? "moderate" : "weak") : undefined}
        />
      </div>
    </div>
  );
}
