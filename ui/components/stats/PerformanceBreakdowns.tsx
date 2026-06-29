"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";

import type { TradeStats } from "@/lib/types";

import { fmt } from "@/lib/format";

interface PerformanceBreakdownsProps {
  stats: TradeStats | null;
  loading: boolean;
  onDrillDown?: (dimension: string, value: string) => void;
}

type TabKey = "day" | "session";

interface RowData {
  name: string;
  total: number;
  winRate: number | null;
  pnl: number;
  filterKey: string;
  filterValue: string;
}

const TABS: { key: TabKey; label: string }[] = [
  { key: "day", label: "Day of Week" },
  { key: "session", label: "Session" },
];

function buildRows(stats: TradeStats | null, tab: TabKey): RowData[] {
  if (!stats) return [];
  const source = tab === "day" ? stats.by_day_of_week : stats.by_session;
  if (!source) return [];
  return Object.entries(source)
    .map(([key, d]) => ({
      name: "name" in d ? (d as { name: string }).name : key,
      total: d.total,
      winRate: d.win_rate,
      pnl: d.total_pnl_usd ?? (d as { total_pnl_points?: number }).total_pnl_points ?? 0,
      filterKey: "",
      filterValue: key,
    }))
    .sort((a, b) => b.pnl - a.pnl);
}

function MiniBar({ rate }: { rate: number | null }) {
  if (rate == null) return null;
  const fill = rate >= 50 ? "#26a69a" : "#ef5350";
  return (
    <div className="h-1 rounded-full bg-[#1e1e1e] w-full mt-0.5 overflow-hidden">
      <div className="h-full rounded-full" style={{ width: `${rate}%`, backgroundColor: fill }} />
    </div>
  );
}

interface TableRowProps {
  row: RowData;
  onJournal: (row: RowData) => void;
  onDrillDown?: (dimension: string, value: string) => void;
  tab: TabKey;
}

function TableRow({ row, onJournal, onDrillDown, tab }: TableRowProps) {
  const wrColor = row.winRate == null ? "text-text-muted"
    : row.winRate >= 65 ? "text-bull font-semibold"
    : row.winRate >= 50 ? "text-bull/70"
    : "text-bear";
  const pnlColor = row.pnl >= 0 ? "text-bull" : "text-bear";

  function handleRowClick() {
    if (onDrillDown && tab !== "day" && tab !== "session") {
      onDrillDown(tab, row.filterValue);
    }
  }

  return (
    <div
      className="grid items-center py-2 border-b border-b-[#1a1a1a] hover:bg-elevated/40 cursor-pointer group"
      style={{ gridTemplateColumns: "1fr 3.5rem 4rem 5rem" }}
      onClick={handleRowClick}
    >
      <span className="text-sm text-text-primary truncate pr-2">{row.name}</span>
      <span className="text-xs text-text-muted text-right tabular-nums">{row.total}</span>
      <div className="px-1">
        <span className={`text-xs text-right tabular-nums block ${wrColor}`}>
          {row.winRate != null ? `${fmt(row.winRate)}%` : "—"}
        </span>
        <MiniBar rate={row.winRate} />
      </div>
      <div className="flex items-center justify-end gap-1">
        <span className={`text-xs tabular-nums ${pnlColor}`}>
          {row.pnl >= 0 ? "+" : ""}${fmt(row.pnl, 0)}
        </span>
        {row.filterKey && (
          <button
            type="button"
            onClick={(e) => { e.stopPropagation(); onJournal(row); }}
            className="text-text-dim opacity-0 group-hover:opacity-100 transition-opacity text-xs ml-1"
            aria-label={`View ${row.name} in journal`}
          >
            →
          </button>
        )}
      </div>
    </div>
  );
}

export function PerformanceBreakdowns({ stats, loading, onDrillDown }: PerformanceBreakdownsProps) {
  const [tab, setTab] = useState<TabKey>("day");
  const router = useRouter();
  const rows = useMemo(() => buildRows(stats, tab), [stats, tab]);
  const dim = loading ? "opacity-50" : "";

  function handleJournal(row: RowData) {
    if (!row.filterKey) return;
    const params = new URLSearchParams();
    params.set(row.filterKey, row.filterValue);
    router.push(`/journal?${params.toString()}`);
  }

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <div className="flex gap-0 mb-4 border-b border-border">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-xs font-medium -mb-px ${
              tab === t.key
                ? "text-yellow-400 border-b-2 border-yellow-400"
                : "text-text-muted hover:text-text-primary border-b-2 border-transparent"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {rows.length === 0 ? (
        <p className="text-text-dim text-sm py-8 text-center">No data available</p>
      ) : (
        <>
          <div
            className="flex items-center pb-1 mb-1"
            style={{ display: "grid", gridTemplateColumns: "1fr 3.5rem 4rem 5rem" }}
          >
            <span className="text-xs text-text-dim">Name</span>
            <span className="text-xs text-text-dim text-right">Trades</span>
            <span className="text-xs text-text-dim text-right px-1">Win %</span>
            <span className="text-xs text-text-dim text-right">P&L</span>
          </div>
          {rows.map((row) => (
            <TableRow
              key={row.filterValue}
              row={row}
              tab={tab}
              onJournal={handleJournal}
              onDrillDown={onDrillDown}
            />
          ))}
        </>
      )}
    </div>
  );
}
