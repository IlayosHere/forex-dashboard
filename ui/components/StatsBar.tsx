"use client";

import type { TradeStats } from "@/lib/types";

const STARTING_BALANCE = 50_000;

interface StatsBarProps {
  stats: TradeStats | null;
  loading: boolean;
}

function fmt(v: number | null | undefined, decimals = 1): string {
  if (v === null || v === undefined) return "—";
  return v.toFixed(decimals);
}

function pnlColor(v: number | null | undefined): string {
  if (v === null || v === undefined || v === 0) return "#777777";
  return v > 0 ? "#26a69a" : "#ef5350";
}

function streakText(streak: number): { text: string; color: string } {
  if (streak === 0) return { text: "—", color: "#777777" };
  if (streak > 0) return { text: `W${streak}`, color: "#26a69a" };
  return { text: `L${Math.abs(streak)}`, color: "#ef5350" };
}

export function StatsBar({ stats, loading }: StatsBarProps) {
  const dim = loading || !stats ? "opacity-50" : "";
  const s = stats;
  const streak = streakText(s?.current_streak ?? 0);
  const pnlPct = s ? (s.total_pnl_usd / STARTING_BALANCE) * 100 : null;

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
        primary={pnlPct != null ? `${pnlPct >= 0 ? "+" : ""}${fmt(pnlPct, 2)}%` : "—"}
        primaryColor={pnlColor(pnlPct)}
        secondary={s ? `${s.total_pnl_usd >= 0 ? "+" : ""}$${fmt(s.total_pnl_usd, 2)}` : undefined}
      />
      <StatCard
        title="Avg R:R"
        primary={s?.avg_rr != null ? fmt(s.avg_rr, 2) : "—"}
      />
      <StatCard
        title="Streak"
        primary={streak.text}
        primaryColor={streak.color}
      />
      <StatCard
        title="Profit Factor"
        primary={s?.profit_factor != null ? fmt(s.profit_factor, 2) : "—"}
      />
    </div>
  );
}

function StatCard({
  title,
  primary,
  primaryColor,
  secondary,
}: {
  title: string;
  primary: string;
  primaryColor?: string;
  secondary?: string;
}) {
  return (
    <div
      className="shrink-0 border border-[#2a2a2a] rounded px-4 py-3 min-w-[120px]"
      style={{ backgroundColor: "#161616" }}
    >
      <div className="label mb-1">{title}</div>
      <div
        className="text-lg font-bold"
        style={{
          color: primaryColor ?? "#e0e0e0",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {primary}
      </div>
      {secondary && (
        <div className="text-xs text-[#777777] mt-0.5">{secondary}</div>
      )}
    </div>
  );
}
