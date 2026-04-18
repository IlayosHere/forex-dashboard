"use client";

import { useState, useMemo } from "react";

import type { IctStatsResponse, IctBucketStats } from "@/lib/types";

interface IctBreakdownsProps {
  data: IctStatsResponse | null;
  loading: boolean;
}

type TabKey = "setup_type" | "tp_target" | "ifvg_timeframe" | "mnq_session";

const TABS: { key: TabKey; label: string }[] = [
  { key: "setup_type", label: "Setup Type" },
  { key: "tp_target", label: "TP Target" },
  { key: "ifvg_timeframe", label: "IFVG Timeframe" },
  { key: "mnq_session", label: "MNQ Session" },
];

const SETUP_TYPE_LABELS: Record<string, string> = {
  liquidity_sweep: "Liquidity Sweep",
  unmitigated_fvg: "Unmitigated FVG",
  continuation: "Continuation",
  other: "Other",
};

const MNQ_SESSION_LABELS: Record<string, string> = {
  am: "AM (9:30–11:30)",
  lunch: "Lunch (11:30–13:00)",
  pm: "PM (13:00–16:00)",
  other: "Other",
};

function toTitleCase(key: string): string {
  return key
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function getLabel(tab: TabKey, key: string): string {
  if (tab === "setup_type") return SETUP_TYPE_LABELS[key] ?? toTitleCase(key);
  if (tab === "mnq_session") return MNQ_SESSION_LABELS[key] ?? toTitleCase(key);
  return toTitleCase(key);
}

function getSource(data: IctStatsResponse, tab: TabKey): Record<string, IctBucketStats> {
  if (tab === "setup_type") return data.by_setup_type;
  if (tab === "tp_target") return data.by_tp_target;
  if (tab === "ifvg_timeframe") return data.by_ifvg_timeframe;
  return data.by_mnq_session;
}

function formatPnl(value: number): string {
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}$${Math.abs(value).toFixed(0)}`;
}

function WinRateCell({ value }: { value: number | null }) {
  if (value === null) return <span className="text-sm font-medium w-14 text-right tabular-nums text-text-muted">—</span>;
  const color = value >= 50 ? "text-bull" : "text-bear";
  return <span className={`text-sm font-medium w-14 text-right tabular-nums ${color}`}>{value.toFixed(0)}%</span>;
}

function PnlCell({ value }: { value: number }) {
  const color = value >= 0 ? "text-bull" : "text-bear";
  return <span className={`text-sm font-medium w-20 text-right tabular-nums ${color}`}>{formatPnl(value)}</span>;
}

interface BreakdownRowProps {
  name: string;
  stats: IctBucketStats;
  accent?: boolean;
}

function BreakdownRow({ name, stats, accent }: BreakdownRowProps) {
  return (
    <div className={`flex items-center justify-between py-2 border-b border-b-[#1a1a1a] ${accent ? "border-l-2 border-l-bull pl-2" : ""}`}>
      <span className="text-sm text-text-primary flex-1">{name}</span>
      <span className="text-xs text-text-muted w-12 text-right">{stats.total}</span>
      <WinRateCell value={stats.win_rate} />
      <PnlCell value={stats.total_pnl_usd} />
    </div>
  );
}

export function IctBreakdowns({ data, loading }: IctBreakdownsProps) {
  const [tab, setTab] = useState<TabKey>("setup_type");
  const dim = loading ? "opacity-50" : "";

  const rows = useMemo(() => {
    if (!data) return [];
    const source = getSource(data, tab);
    return Object.entries(source)
      .map(([key, stats]) => ({ key, name: getLabel(tab, key), stats }))
      .sort((a, b) => b.stats.total_pnl_usd - a.stats.total_pnl_usd);
  }, [data, tab]);

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <p className="text-xs uppercase tracking-widest text-text-muted mb-4">ICT Setup Analysis</p>

      <div className="flex gap-0 border-b border-border mb-4">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-xs font-medium -mb-px ${
              tab === t.key
                ? "text-bull border-b-2 border-bull"
                : "text-text-muted hover:text-text-primary border-b-2 border-transparent"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="flex items-center justify-between pb-1 mb-1">
        <span className="text-xs text-text-dim flex-1">Name</span>
        <span className="text-xs text-text-dim w-12 text-right">Trades</span>
        <span className="text-xs text-text-dim w-14 text-right">Win %</span>
        <span className="text-xs text-text-dim w-20 text-right">P&L (USD)</span>
      </div>

      {rows.length === 0 ? (
        <p className="text-text-dim text-sm py-6 text-center">No data available</p>
      ) : (
        rows.map(({ key, name, stats }) => (
          <BreakdownRow
            key={key}
            name={name}
            stats={stats}
            accent={tab === "mnq_session" && key === "am"}
          />
        ))
      )}
    </div>
  );
}
