"use client";

import type { TradeStats } from "@/lib/types";

import { fmt } from "@/lib/format";

interface ComplianceBucket {
  total: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  total_pnl_usd: number;
}

interface TradeStatsWithCompliance extends TradeStats {
  by_rule_compliance?: {
    compliant?: ComplianceBucket;
    mistake?: ComplianceBucket;
    unreviewed?: ComplianceBucket;
  };
}

interface StatsBarProps {
  stats: TradeStatsWithCompliance | null;
  loading: boolean;
}

function pnlColorClass(v: number | null | undefined): string {
  if (v === null || v === undefined || v === 0) return "text-text-muted";
  return v > 0 ? "text-bull" : "text-bear";
}

function streakText(streak: number): { text: string; colorClass: string } {
  if (streak === 0) return { text: "—", colorClass: "text-text-muted" };
  if (streak > 0) return { text: `W${streak}`, colorClass: "text-bull" };
  return { text: `L${Math.abs(streak)}`, colorClass: "text-bear" };
}

export function StatsBar({ stats, loading }: StatsBarProps) {
  const dim = loading || !stats ? "opacity-50" : "";
  const s = stats;
  const streak = streakText(s?.current_streak ?? 0);

  return (
    <div className={`flex gap-3 overflow-x-auto pb-1 ${dim}`}>
      <StatCard
        title="Win Rate"
        primary={s?.win_rate != null ? `${fmt(s.win_rate)}%` : "—"}
        secondary={s ? `${s.wins}W ${s.losses}L` : "—"}
      />
      <StatCard
        title="Trades"
        primary={s ? String(s.total_trades) : "—"}
        secondary={s?.open_trades ? `${s.open_trades} open` : undefined}
      />
      <StatCard
        title="P&L"
        primary={s ? `${s.total_pnl_usd >= 0 ? "+$" : "-$"}${Math.abs(s.total_pnl_usd).toFixed(2)}` : "—"}
        primaryColorClass={pnlColorClass(s?.total_pnl_usd)}
      />
      <StatCard
        title="Avg R:R"
        primary={s?.avg_rr != null ? fmt(s.avg_rr, 2) : "—"}
      />
      <StatCard
        title="Streak"
        primary={streak.text}
        primaryColorClass={streak.colorClass}
      />
      <StatCard
        title="Profit Factor"
        primary={s?.profit_factor != null ? fmt(s.profit_factor, 2) : "—"}
      />
      <ComplianceStatCard stats={s} />
    </div>
  );
}

function ComplianceStatCard({ stats }: { stats: TradeStatsWithCompliance | null }) {
  const compliantTotal = stats?.by_rule_compliance?.compliant?.total ?? 0;
  const mistakeTotal = stats?.by_rule_compliance?.mistake?.total ?? 0;
  const reviewed = compliantTotal + mistakeTotal;
  const complianceRate = reviewed > 0 ? Math.round((compliantTotal / reviewed) * 100) : null;

  return (
    <StatCard
      title="Compliance"
      primary={complianceRate !== null ? `${complianceRate}%` : "—"}
      secondary={`${compliantTotal} ok / ${mistakeTotal} mistakes`}
    />
  );
}

function StatCard({
  title,
  primary,
  primaryColorClass,
  secondary,
}: {
  title: string;
  primary: string;
  primaryColorClass?: string;
  secondary?: string;
}) {
  return (
    <div className="shrink-0 border border-border rounded px-4 py-3 min-w-[120px] bg-card">
      <div className="label mb-1">{title}</div>
      <div
        className={`text-lg font-bold tabular-nums ${primaryColorClass ?? "text-text-primary"}`}
      >
        {primary}
      </div>
      {secondary && (
        <div className="text-xs text-muted-foreground mt-0.5">{secondary}</div>
      )}
    </div>
  );
}
