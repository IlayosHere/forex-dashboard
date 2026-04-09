"use client";

import { useMemo } from "react";

import type { DailySummaryPoint } from "@/lib/types";

import { fmt } from "@/lib/format";

interface CalendarHeatmapProps {
  data: DailySummaryPoint[];
  loading: boolean;
}

interface DayCell {
  date: string;
  pnl: number;
  trades: number;
  wins: number;
  losses: number;
  col: number;
  row: number;
}

const DAY_LABELS = ["Mon", "", "Wed", "", "Fri", "", ""];
const MONTHS_TO_SHOW = 6;

function getColor(pnl: number, maxAbs: number): string {
  if (pnl === 0) return "#1a1a1a";
  const intensity = Math.min(Math.abs(pnl) / (maxAbs || 1), 1);
  const alpha = 0.2 + intensity * 0.8;
  return pnl > 0
    ? `rgba(38, 166, 154, ${alpha})`
    : `rgba(239, 83, 80, ${alpha})`;
}

function buildGrid(data: DailySummaryPoint[]): { cells: DayCell[]; months: { label: string; col: number }[]; maxAbs: number } {
  const today = new Date();
  const start = new Date(today);
  start.setMonth(start.getMonth() - MONTHS_TO_SHOW);
  start.setDate(1);

  const dayOfWeek = (start.getDay() + 6) % 7;
  start.setDate(start.getDate() - dayOfWeek);

  const pnlMap = new Map<string, DailySummaryPoint>();
  for (const d of data) pnlMap.set(d.date, d);

  const cells: DayCell[] = [];
  const months: { label: string; col: number }[] = [];
  let lastMonth = -1;
  let maxAbs = 0;

  const cursor = new Date(start);
  let col = 0;

  while (cursor <= today) {
    const m = cursor.getMonth();
    if (m !== lastMonth) {
      months.push({ label: cursor.toLocaleDateString("en-US", { month: "short" }), col });
      lastMonth = m;
    }

    for (let row = 0; row < 7; row++) {
      if (cursor > today) break;
      const key = cursor.toISOString().slice(0, 10);
      const entry = pnlMap.get(key);
      const pnl = entry?.pnl_usd ?? 0;
      const trades = entry?.trades ?? 0;
      if (Math.abs(pnl) > maxAbs) maxAbs = Math.abs(pnl);

      cells.push({
        date: key,
        pnl,
        trades,
        wins: entry?.wins ?? 0,
        losses: entry?.losses ?? 0,
        col,
        row,
      });
      cursor.setDate(cursor.getDate() + 1);
    }
    col++;
  }

  return { cells, months, maxAbs };
}

export function CalendarHeatmap({ data, loading }: CalendarHeatmapProps) {
  const { cells, months, maxAbs } = useMemo(() => buildGrid(data), [data]);
  const dim = loading ? "opacity-50" : "";

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Daily P&L</h3>

      {/* Month labels */}
      <div className="flex gap-0 ml-8 mb-1">
        {months.map((m, i) => {
          const nextCol = i < months.length - 1 ? months[i + 1].col : (cells.length > 0 ? cells[cells.length - 1].col + 1 : m.col + 4);
          const span = nextCol - m.col;
          return (
            <div
              key={`${m.label}-${m.col}`}
              className="text-[10px] text-text-dim"
              style={{ width: `${span * 14}px` }}
            >
              {m.label}
            </div>
          );
        })}
      </div>

      <div className="flex gap-0">
        {/* Day of week labels */}
        <div className="flex flex-col gap-[2px] mr-1 shrink-0">
          {DAY_LABELS.map((label, i) => (
            <div key={i} className="h-[12px] text-[9px] text-text-dim leading-[12px] w-7 text-right pr-1">
              {label}
            </div>
          ))}
        </div>

        {/* Grid */}
        <div className="relative">
          {cells.map((cell) => (
            <div
              key={cell.date}
              className="absolute rounded-[2px] group"
              style={{
                left: cell.col * 14,
                top: cell.row * 14,
                width: 11,
                height: 11,
                backgroundColor: cell.trades > 0 ? getColor(cell.pnl, maxAbs) : "#1a1a1a",
              }}
            >
              {cell.trades > 0 && (
                <div className="hidden group-hover:block absolute z-20 bottom-full left-1/2 -translate-x-1/2 mb-1 bg-surface-raised border border-border rounded px-2 py-1 text-[10px] whitespace-nowrap">
                  <div className="text-text-primary">{cell.date}</div>
                  <div style={{ color: cell.pnl >= 0 ? "#26a69a" : "#ef5350" }}>
                    {cell.pnl >= 0 ? "+" : ""}${fmt(cell.pnl, 2)}
                  </div>
                  <div className="text-text-muted">
                    {cell.trades} trades ({cell.wins}W / {cell.losses}L)
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
