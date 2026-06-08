"use client";

import { useMemo } from "react";

import type { IctIfvgBarsRow } from "@/lib/ictTypes";

interface IctIfvgBarsMatrixProps {
  rows: IctIfvgBarsRow[];
  loading: boolean;
}

const BARS_ORDER = ["1","2","3","4","5","6","7","8","9","10","10+"];

function sortedTimeframes(rows: IctIfvgBarsRow[]): string[] {
  const tfs = Array.from(new Set(rows.map((r) => r.timeframe)));
  const tfSeconds = (tf: string) => {
    if (tf === "other") return 999999;
    if (tf.endsWith("s")) return parseInt(tf, 10);
    return parseInt(tf, 10) * 60;
  };
  return tfs.sort((a, b) => tfSeconds(a) - tfSeconds(b));
}

function WinRateCell({ value }: { value: number | null }) {
  if (value === null) return <span className="text-text-dim">—</span>;
  const color = value >= 55 ? "text-bull" : value >= 45 ? "text-text-muted" : "text-bear";
  return <span className={`font-medium tabular-nums ${color}`}>{value.toFixed(0)}%</span>;
}

function MatrixCell({ row }: { row: IctIfvgBarsRow | undefined }) {
  if (!row) {
    return (
      <td className="px-2 py-1.5 text-center text-text-dim text-xs border border-[#1a1a1a]">—</td>
    );
  }
  return (
    <td className="px-2 py-1.5 text-center border border-[#1a1a1a] min-w-[68px]">
      <div className="text-xs">
        <WinRateCell value={row.win_rate} />
      </div>
      <div className="text-[10px] text-text-dim tabular-nums">{row.total}t</div>
    </td>
  );
}

export function IctIfvgBarsMatrix({ rows, loading }: IctIfvgBarsMatrixProps) {
  const dim = loading ? "opacity-50" : "";

  const timeframes = useMemo(() => sortedTimeframes(rows), [rows]);

  // Build lookup: bars_label+timeframe -> row
  const lookup = useMemo(() => {
    const map = new Map<string, IctIfvgBarsRow>();
    for (const row of rows) {
      map.set(`${row.bars_label}|${row.timeframe}`, row);
    }
    return map;
  }, [rows]);

  // Only show bars labels that have at least one data point
  const barsLabels = useMemo(
    () => BARS_ORDER.filter((b) => rows.some((r) => r.bars_label === b)),
    [rows],
  );

  if (rows.length === 0) {
    return (
      <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
        <p className="text-xs uppercase tracking-widest text-text-muted mb-3">Bars to IFVG × Timeframe</p>
        <p className="text-text-dim text-sm py-6 text-center">No data — start logging Bars to IFVG on your trades</p>
      </div>
    );
  }

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <p className="text-xs uppercase tracking-widest text-text-muted mb-1">Bars to IFVG × Timeframe</p>
      <p className="text-[10px] text-text-dim mb-4">Win % / trade count per cell. Green ≥ 55 %, red &lt; 45 %.</p>

      <div className="overflow-x-auto">
        <table className="text-xs border-collapse w-full">
          <thead>
            <tr>
              <th className="px-2 py-1.5 text-left text-text-muted font-normal border border-[#1a1a1a] bg-[#111]">
                Bars ↓ / TF →
              </th>
              {timeframes.map((tf) => (
                <th
                  key={tf}
                  className="px-2 py-1.5 text-center text-text-muted font-normal border border-[#1a1a1a] bg-[#111] uppercase"
                >
                  {tf}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {barsLabels.map((bars) => (
              <tr key={bars}>
                <td className="px-2 py-1.5 text-text-muted font-medium border border-[#1a1a1a] bg-[#111] tabular-nums">
                  {bars}
                </td>
                {timeframes.map((tf) => (
                  <MatrixCell key={tf} row={lookup.get(`${bars}|${tf}`)} />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
