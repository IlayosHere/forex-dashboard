"use client";

import { useMemo, useState } from "react";

import type { TimeEdgeStats, TimeMatrixCell } from "@/lib/ictTypes";

import {
  expectancyColor,
  formatExpectancy,
  formatWinRate,
  heatBackground,
  MATRIX_TABS,
  PHASE_ORDER,
  PHASE_SHORT,
  rowLabel,
} from "@/lib/timeEdgeHelpers";

interface TimeCrossMatrixProps {
  timeEdge: TimeEdgeStats;
  loading: boolean;
}

const WEEKDAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function sortRows(tabKey: string, rows: string[]): string[] {
  if (tabKey === "weekday") return [...rows].sort((a, b) => WEEKDAY_ORDER.indexOf(a) - WEEKDAY_ORDER.indexOf(b));
  return [...rows].sort();
}

function MatrixCell({ cell, minSample }: { cell: TimeMatrixCell | undefined; minSample: number }) {
  if (!cell) return <td className="p-1"><div className="h-12 rounded bg-[#141414]" /></td>;
  const { stats } = cell;
  const thin = stats.total < minSample;
  return (
    <td className="p-1">
      <div
        className={`h-12 rounded flex flex-col items-center justify-center ${thin ? "opacity-70" : ""}`}
        style={{ backgroundColor: heatBackground(stats, minSample) }}
        title={`${stats.total} trades · ${formatWinRate(stats.win_rate)} win · ${formatExpectancy(stats.expectancy_r)}`}
      >
        <span className="text-xs font-medium tabular-nums" style={{ color: expectancyColor(stats.expectancy_r) }}>
          {formatExpectancy(stats.expectancy_r)}
        </span>
        <span className="text-[10px] text-text-muted tabular-nums">
          {formatWinRate(stats.win_rate)} · n={stats.total}
        </span>
      </div>
    </td>
  );
}

export function TimeCrossMatrix({ timeEdge, loading }: TimeCrossMatrixProps) {
  const [tab, setTab] = useState(MATRIX_TABS[0].key);
  const cells = useMemo(() => timeEdge.matrices[tab] ?? [], [timeEdge, tab]);

  const { rows, phases, lookup } = useMemo(() => {
    const present = new Set(cells.map((c) => c.phase));
    return {
      rows: sortRows(tab, [...new Set(cells.map((c) => c.row))]),
      phases: PHASE_ORDER.filter((p) => present.has(p)),
      lookup: new Map(cells.map((c) => [`${c.row}|${c.phase}`, c])),
    };
  }, [cells, tab]);

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${loading ? "opacity-50" : ""}`}>
      <p className="text-xs uppercase tracking-widest text-text-muted mb-4">What works when</p>
      <div className="flex flex-wrap gap-0 border-b border-border mb-3">
        {MATRIX_TABS.map((t) => (
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

      {rows.length === 0 ? (
        <p className="text-text-dim text-sm py-6 text-center">
          No trades with this field logged yet — fill it in when journaling to unlock this view.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="text-left text-xs text-text-dim font-normal p-1 w-32" />
                {phases.map((p) => (
                  <th key={p} className="text-xs text-text-dim font-normal p-1 min-w-24">{PHASE_SHORT[p]}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row}>
                  <td className="text-xs text-text-primary p-1 pr-3">{rowLabel(tab, row)}</td>
                  {phases.map((p) => (
                    <MatrixCell key={p} cell={lookup.get(`${row}|${p}`)} minSample={timeEdge.min_sample} />
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="text-[10px] text-text-dim mt-2">
        Cell = expectancy in R · win rate · trade count. Faded cells have fewer than {timeEdge.min_sample} trades.
      </p>
    </div>
  );
}
