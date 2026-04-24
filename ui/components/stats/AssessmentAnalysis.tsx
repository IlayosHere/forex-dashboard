"use client";

import { useMemo } from "react";

import type { BreakdownEntry } from "@/lib/types";

import { fmt } from "@/lib/format";

interface AssessmentAnalysisProps {
  byConfidence: Record<string, BreakdownEntry> | undefined;
  byRating: Record<string, BreakdownEntry> | undefined;
  loading: boolean;
}

interface LevelRow {
  level: string;
  total: number;
  winRate: number | null;
  avgPnl: number;
}

function buildRows(map: Record<string, BreakdownEntry> | undefined): LevelRow[] {
  const rows: LevelRow[] = [];
  for (let i = 1; i <= 5; i++) {
    const entry = map?.[String(i)];
    rows.push({
      level: String(i),
      total: entry?.total ?? 0,
      winRate: entry?.win_rate ?? null,
      avgPnl: entry?.avg_pnl_usd ?? 0,
    });
  }
  return rows;
}

function winRateClass(rate: number | null): string {
  if (rate == null) return "text-text-muted";
  if (rate >= 65) return "text-bull font-semibold";
  if (rate >= 50) return "text-bull/70";
  return "text-bear";
}

function LevelTable({ title, rows }: { title: string; rows: LevelRow[] }) {
  const hasData = rows.some((r) => r.total > 0);

  return (
    <div className="flex-1 min-w-0">
      <p className="text-[10px] uppercase tracking-widest text-text-muted mb-3">{title}</p>
      {!hasData ? (
        <p className="text-text-dim text-sm py-6 text-center">No data</p>
      ) : (
        <>
          <div
            className="grid pb-1 mb-1"
            style={{ gridTemplateColumns: "2.5rem 3.5rem 4rem 5rem" }}
          >
            <span className="text-xs text-text-dim">Lvl</span>
            <span className="text-xs text-text-dim text-right">Trades</span>
            <span className="text-xs text-text-dim text-right">Win %</span>
            <span className="text-xs text-text-dim text-right">Avg P&L</span>
          </div>
          {rows.map((row) => {
            if (row.total === 0) return null;
            const pnlColor = row.avgPnl >= 0 ? "#26a69a" : "#ef5350";
            return (
              <div
                key={row.level}
                className="grid items-center py-2 border-b border-b-[#1a1a1a]"
                style={{ gridTemplateColumns: "2.5rem 3.5rem 4rem 5rem" }}
              >
                <span className="text-sm text-text-primary tabular-nums">{row.level}</span>
                <span className="text-xs text-text-muted text-right tabular-nums">{row.total}</span>
                <span className={`text-xs text-right tabular-nums ${winRateClass(row.winRate)}`}>
                  {row.winRate != null ? `${fmt(row.winRate)}%` : "—"}
                </span>
                <span className="text-xs text-right tabular-nums" style={{ color: pnlColor }}>
                  {row.avgPnl >= 0 ? "+" : ""}${fmt(row.avgPnl, 2)}
                </span>
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}

export function AssessmentAnalysis({ byConfidence, byRating, loading }: AssessmentAnalysisProps) {
  const confidenceRows = useMemo(() => buildRows(byConfidence), [byConfidence]);
  const ratingRows = useMemo(() => buildRows(byRating), [byRating]);
  const dim = loading ? "opacity-50" : "";

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <div className="grid grid-cols-2 gap-6">
        <LevelTable title="By Confidence Level" rows={confidenceRows} />
        <LevelTable title="By Rating Level" rows={ratingRows} />
      </div>
    </div>
  );
}
