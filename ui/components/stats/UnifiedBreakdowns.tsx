"use client";

import { useState, useMemo } from "react";

import type { IctStatsResponse } from "@/lib/ictTypes";
import type { TradeStats } from "@/lib/types";

import {
  ALL_TABS,
  buildRows,
  buildSmtTdoSections,
} from "@/components/stats/unifiedBreakdownsHelpers";
import type { UnifiedRow, SmtTdoSection, UnifiedTabKey } from "@/components/stats/unifiedBreakdownsHelpers";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface UnifiedBreakdownsProps {
  stats: TradeStats | null;
  ictStats: IctStatsResponse | null;
  loading: boolean;
}

// ---------------------------------------------------------------------------
// Cell helpers
// ---------------------------------------------------------------------------

function winRateClass(v: number | null): string {
  if (v === null) return "text-text-muted";
  if (v >= 65) return "text-bull font-semibold";
  if (v >= 50) return "text-bull/70";
  return "text-bear";
}

function WinRateCell({ v }: { v: number | null }) {
  return (
    <span className={`text-xs tabular-nums text-right ${winRateClass(v)}`}>
      {v !== null ? `${v.toFixed(0)}%` : "—"}
    </span>
  );
}

function NumCell({ v, decimals = 2 }: { v: number | null; decimals?: number }) {
  if (v === null) return <span className="text-xs tabular-nums text-text-muted">—</span>;
  const color = v >= 0 ? "text-bull" : "text-bear";
  return (
    <span className={`text-xs tabular-nums ${color}`}>
      {v >= 0 ? "+" : ""}
      {v.toFixed(decimals)}
    </span>
  );
}

function PnlCell({ v }: { v: number }) {
  const color = v >= 0 ? "text-bull" : "text-bear";
  const sign = v >= 0 ? "+" : "−";
  return (
    <span className={`text-xs tabular-nums ${color}`}>
      {sign}${Math.abs(v).toFixed(0)}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Table
// ---------------------------------------------------------------------------

const COL_GRID = "grid-cols-[1fr_3rem_4rem_4.5rem_4.5rem_4.5rem]";

function TableHeader() {
  return (
    <div className={`grid ${COL_GRID} pb-1 mb-1 border-b border-border`}>
      <span className="text-xs text-text-dim">Bucket</span>
      <span className="text-xs text-text-dim text-right">Trades</span>
      <span className="text-xs text-text-dim text-right">Win%</span>
      <span className="text-xs text-text-dim text-right">Avg R</span>
      <span className="text-xs text-text-dim text-right">Exp(R)</span>
      <span className="text-xs text-text-dim text-right">Net P&L</span>
    </div>
  );
}

function TableRow({ row }: { row: UnifiedRow }) {
  return (
    <div className={`grid ${COL_GRID} items-center py-1.5 border-b border-b-[#1a1a1a]`}>
      <span className="text-xs text-text-primary truncate pr-2">{row.label}</span>
      <span className="text-xs text-text-muted text-right tabular-nums">{row.total}</span>
      <div className="flex justify-end"><WinRateCell v={row.winRate} /></div>
      <div className="flex justify-end"><NumCell v={row.avgRr} /></div>
      <div className="flex justify-end"><NumCell v={row.expectancyR} /></div>
      <div className="flex justify-end"><PnlCell v={row.netPnl} /></div>
    </div>
  );
}

function BreakdownTable({ rows }: { rows: UnifiedRow[] }) {
  if (rows.length === 0) {
    return <p className="text-text-dim text-sm py-8 text-center">No data available</p>;
  }
  return (
    <>
      <TableHeader />
      {rows.map((r) => <TableRow key={r.key} row={r} />)}
    </>
  );
}

// ---------------------------------------------------------------------------
// SMT/TDO special layout
// ---------------------------------------------------------------------------

function SmtTdoSubTable({ section }: { section: SmtTdoSection }) {
  return (
    <div className="flex-1 min-w-0">
      <p className="text-xs text-text-muted mb-2 font-medium">{section.title}</p>
      <TableHeader />
      <TableRow row={section.trueRow} />
      <TableRow row={section.falseRow} />
    </div>
  );
}

function SmtTdoTab({ ictStats }: { ictStats: IctStatsResponse }) {
  const sections = useMemo(() => buildSmtTdoSections(ictStats), [ictStats]);
  if (sections.length === 0) {
    return <p className="text-text-dim text-sm py-8 text-center">No data available</p>;
  }
  return (
    <div className="flex gap-6 flex-wrap">
      {sections.map((s) => <SmtTdoSubTable key={s.title} section={s} />)}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab bar
// ---------------------------------------------------------------------------

function TabBar({
  activeTab,
  hasIct,
  onSelect,
}: {
  activeTab: UnifiedTabKey;
  hasIct: boolean;
  onSelect: (key: UnifiedTabKey) => void;
}) {
  const visible = ALL_TABS.filter((t) => !t.requiresIct || hasIct);
  return (
    <div className="flex flex-wrap gap-0 border-b border-border mb-4">
      {visible.map((t) => (
        <button
          key={t.key}
          type="button"
          onClick={() => onSelect(t.key)}
          className={`px-3 py-2 text-xs font-medium -mb-px whitespace-nowrap ${
            activeTab === t.key
              ? "text-yellow-400 border-b-2 border-yellow-400"
              : "text-text-muted hover:text-text-primary border-b-2 border-transparent"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function UnifiedBreakdowns({ stats, ictStats, loading }: UnifiedBreakdownsProps) {
  const [activeTab, setActiveTab] = useState<UnifiedTabKey>("session");

  const rows = useMemo(
    () => buildRows(activeTab, stats, ictStats),
    [activeTab, stats, ictStats]
  );

  const isSmtTdo = activeTab === "smt_tdo";
  const dim = loading ? "opacity-50" : "";

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <TabBar activeTab={activeTab} hasIct={ictStats !== null} onSelect={setActiveTab} />
      {isSmtTdo && ictStats ? (
        <SmtTdoTab ictStats={ictStats} />
      ) : (
        <BreakdownTable rows={rows} />
      )}
    </div>
  );
}
