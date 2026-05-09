"use client";

import type { TradeStats } from "@/lib/types";

import { fmt } from "@/lib/format";
import { complianceRateClass, computeComplianceRate } from "@/lib/statsHelpers";

interface StatsBarProps {
  stats: TradeStats | null;
  loading: boolean;
  mode?: "default" | "backtest";
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

function formatPnl(s: TradeStats | null, isBacktest: boolean): string {
  if (!s) return "—";
  const sign = s.total_pnl_usd >= 0 ? "+" : "-";
  const prefix = isBacktest ? "" : "$";
  return `${sign}${prefix}${Math.abs(s.total_pnl_usd).toFixed(2)}`;
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
      <div className={`text-lg font-bold tabular-nums ${primaryColorClass ?? "text-text-primary"}`}>
        {primary}
      </div>
      {secondary && <div className="text-xs text-muted-foreground mt-0.5">{secondary}</div>}
    </div>
  );
}

function LiveComplianceCard({ stats }: { stats: TradeStats | null }) {
  const compliantCount = stats?.by_rule_compliance?.compliant?.total ?? 0;
  const mistakeCount = stats?.by_rule_compliance?.mistake?.total ?? 0;
  const rate = computeComplianceRate(compliantCount, mistakeCount);

  return (
    <StatCard
      title="Compliance"
      primary={rate !== null ? `${rate}%` : "—"}
      primaryColorClass={complianceRateClass(rate)}
      secondary={`${compliantCount} ok / ${mistakeCount} mistakes`}
    />
  );
}

function CriteriaMetCard({ stats }: { stats: TradeStats | null }) {
  const metCount = stats?.by_criteria_met?.met?.total ?? 0;
  const notMetCount = stats?.by_criteria_met?.not_met?.total ?? 0;
  const rate = computeComplianceRate(metCount, notMetCount);
  const reviewed = metCount + notMetCount;

  return (
    <StatCard
      title="Criteria Met"
      primary={rate !== null ? `${rate}%` : "—"}
      primaryColorClass={complianceRateClass(rate)}
      secondary={reviewed > 0 ? `${metCount} met / ${notMetCount} not` : "not recorded"}
    />
  );
}

export function StatsBar({ stats, loading, mode = "default" }: StatsBarProps) {
  const dim = loading || !stats ? "opacity-50" : "";
  const isBacktest = mode === "backtest";
  const streak = streakText(stats?.current_streak ?? 0);

  const winRateCard = (
    <StatCard
      title="Win Rate"
      primary={stats?.win_rate != null ? `${fmt(stats.win_rate)}%` : "—"}
      secondary={stats ? `${stats.wins}W ${stats.losses}L` : "—"}
    />
  );
  const avgRrCard = (
    <StatCard
      title="Avg R:R"
      primary={stats?.avg_rr != null ? fmt(stats.avg_rr, 2) : "—"}
    />
  );
  const pnlCard = (
    <StatCard
      title={isBacktest ? "P&L (notional)" : "P&L"}
      primary={formatPnl(stats, isBacktest)}
      primaryColorClass={isBacktest ? "text-text-muted opacity-50" : pnlColorClass(stats?.total_pnl_usd)}
    />
  );

  if (isBacktest) {
    return (
      <div className={`flex gap-3 overflow-x-auto pb-1 ${dim}`}>
        {winRateCard}
        {avgRrCard}
        <StatCard
          title="Trades"
          primary={stats ? String(stats.total_trades) : "—"}
          secondary={stats?.open_trades ? `${stats.open_trades} open` : undefined}
        />
        <StatCard
          title="Profit Factor"
          primary={stats?.profit_factor != null ? fmt(stats.profit_factor, 2) : "—"}
        />
        {pnlCard}
        <CriteriaMetCard stats={stats} />
      </div>
    );
  }

  return (
    <div className={`flex gap-3 overflow-x-auto pb-1 ${dim}`}>
      {winRateCard}
      <StatCard
        title="Trades"
        primary={stats ? String(stats.total_trades) : "—"}
        secondary={stats?.open_trades ? `${stats.open_trades} open` : undefined}
      />
      {pnlCard}
      {avgRrCard}
      <StatCard
        title="Streak"
        primary={streak.text}
        primaryColorClass={streak.colorClass}
      />
      <StatCard
        title="Profit Factor"
        primary={stats?.profit_factor != null ? fmt(stats.profit_factor, 2) : "—"}
      />
      <LiveComplianceCard stats={stats} />
    </div>
  );
}
