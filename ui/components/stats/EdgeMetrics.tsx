"use client";

import type { TradeStats } from "@/lib/types";

import { fmt } from "@/lib/format";

interface EdgeMetricsProps {
  stats: TradeStats | null;
  loading: boolean;
}

function formatHoldTime(hours: number | null): string {
  if (hours === null) return "--";
  if (hours < 1) return `${Math.round(hours * 60)}m`;
  const h = Math.floor(hours);
  const m = Math.round((hours - h) * 60);
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

function MetricRow({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex justify-between items-center py-1.5">
      <span className="text-xs text-text-muted">{label}</span>
      <span className="text-sm font-semibold price" style={{ color: color ?? "#e0e0e0" }}>
        {value}
      </span>
    </div>
  );
}

function MetricCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">{title}</h3>
      <div className="divide-y divide-border">{children}</div>
    </div>
  );
}

export function EdgeMetrics({ stats, loading }: EdgeMetricsProps) {
  const dim = loading ? "opacity-50" : "";
  const s = stats;

  return (
    <div className={`grid grid-cols-1 md:grid-cols-3 gap-3 ${dim}`}>
      {/* Expectancy */}
      <MetricCard title="Expectancy">
        <MetricRow
          label="Per Trade (USD)"
          value={s?.expectancy_usd != null ? `$${fmt(s.expectancy_usd, 2)}` : "--"}
          color={s?.expectancy_usd != null ? (s.expectancy_usd >= 0 ? "#26a69a" : "#ef5350") : undefined}
        />
        <MetricRow
          label="Per Trade (Pips)"
          value={s?.expectancy_pips != null ? fmt(s.expectancy_pips, 1) : "--"}
          color={s?.expectancy_pips != null ? (s.expectancy_pips >= 0 ? "#26a69a" : "#ef5350") : undefined}
        />
        <MetricRow
          label="Avg Win"
          value={s?.avg_win_usd != null ? `$${fmt(s.avg_win_usd, 2)}` : "--"}
          color="#26a69a"
        />
        <MetricRow
          label="Avg Loss"
          value={s?.avg_loss_usd != null ? `-$${fmt(Math.abs(s.avg_loss_usd), 2)}` : "--"}
          color="#ef5350"
        />
      </MetricCard>

      {/* Key Ratios */}
      <MetricCard title="Key Ratios">
        <MetricRow
          label="Profit Factor"
          value={s?.profit_factor != null ? fmt(s.profit_factor, 2) : "--"}
        />
        <MetricRow
          label="Avg R:R"
          value={s?.avg_rr != null ? fmt(s.avg_rr, 2) : "--"}
        />
        <MetricRow
          label="Consistency"
          value={s?.consistency_ratio != null ? `${fmt(s.consistency_ratio)}%` : "--"}
        />
        <MetricRow
          label="Streak"
          value={s ? (s.current_streak === 0 ? "--" : s.current_streak > 0 ? `W${s.current_streak}` : `L${Math.abs(s.current_streak)}`) : "--"}
          color={s ? (s.current_streak > 0 ? "#26a69a" : s.current_streak < 0 ? "#ef5350" : undefined) : undefined}
        />
      </MetricCard>

      {/* Summary */}
      <MetricCard title="Summary">
        <MetricRow label="Total Trades" value={s ? String(s.total_trades) : "--"} />
        <MetricRow
          label="Best Trade"
          value={s?.best_trade_pnl != null ? `$${fmt(s.best_trade_pnl, 2)}` : "--"}
          color={s?.best_trade_pnl != null && s.best_trade_pnl > 0 ? "#26a69a" : undefined}
        />
        <MetricRow
          label="Worst Trade"
          value={s?.worst_trade_pnl != null ? `$${fmt(s.worst_trade_pnl, 2)}` : "--"}
          color={s?.worst_trade_pnl != null && s.worst_trade_pnl < 0 ? "#ef5350" : undefined}
        />
        <MetricRow
          label="Avg Hold Time"
          value={formatHoldTime(s?.avg_hold_time_hours ?? null)}
        />
      </MetricCard>
    </div>
  );
}
