import type { InteractionCell, InteractionResponse } from "@/lib/types";

import { getParamLabel, prettifyBucketLabel } from "@/lib/analyticsParamMeta";

interface InteractionHeatmapProps {
  data: InteractionResponse | null;
  loading: boolean;
}

function cellBackground(winRate: number | null, overall: number): string {
  if (winRate === null) return "rgba(255,255,255,0.04)";
  const diff = winRate - overall;
  if (diff >= 0.10) return "rgba(38,166,154,0.30)";
  if (diff >= 0.05) return "rgba(38,166,154,0.14)";
  if (diff <= -0.10) return "rgba(239,83,80,0.30)";
  if (diff <= -0.05) return "rgba(239,83,80,0.14)";
  return "rgba(255,255,255,0.06)";
}

function cellTextColor(winRate: number | null, overall: number): string {
  if (winRate === null) return "#6b7280";
  const diff = winRate - overall;
  if (diff >= 0.05) return "#26a69a";
  if (diff <= -0.05) return "#ef5350";
  return "#e5e7eb";
}

function CellContent({ cell, overall, paramA, paramB }: {
  cell: InteractionCell;
  overall: number;
  paramA: string;
  paramB: string;
}) {
  const bg = cellBackground(cell.win_rate, overall);
  const color = cellTextColor(cell.win_rate, overall);
  return (
    <td
      className="border border-border text-center px-1 py-1.5 min-w-[64px]"
      style={{ backgroundColor: bg }}
    >
      {cell.win_rate === null ? (
        <span className="text-xs text-text-dim">—</span>
      ) : (
        <>
          <div className="text-xs font-medium tabular-nums" style={{ color }}>
            {Math.round(cell.win_rate * 100)}%
          </div>
          <div className="text-[10px] text-text-dim tabular-nums">n={cell.total}</div>
        </>
      )}
    </td>
  );
}

export function InteractionHeatmap({ data, loading }: InteractionHeatmapProps) {
  if (loading) {
    return (
      <div className="text-sm text-text-dim py-6 text-center animate-pulse">
        Loading heatmap…
      </div>
    );
  }

  if (!data) {
    return (
      <div className="text-sm text-text-dim py-6 text-center">
        Select two parameters to view the interaction heatmap.
      </div>
    );
  }

  const { param_a, param_b, buckets_a, buckets_b, cells, overall_win_rate } = data;
  const labelA = getParamLabel(param_a);
  const labelB = getParamLabel(param_b);

  const cellMap = new Map<string, InteractionCell>();
  for (const cell of cells) {
    cellMap.set(`${cell.bucket_a}||${cell.bucket_b}`, cell);
  }

  return (
    <div className="overflow-x-auto">
      <div className="mb-2 flex items-center gap-4">
        <span className="text-xs text-text-muted">
          Overall win rate: <span className="text-text-primary font-medium">{Math.round(overall_win_rate * 100)}%</span>
        </span>
        <span className="text-xs text-text-dim">
          Cells with fewer than 15 signals are greyed out
        </span>
      </div>

      <table className="border-collapse text-xs">
        <thead>
          <tr>
            <th className="border border-border px-2 py-1 text-left text-text-muted font-medium">
              {labelA} ↓ / {labelB} →
            </th>
            {buckets_b.map((b) => (
              <th
                key={b}
                className="border border-border px-2 py-1 text-text-muted font-medium whitespace-nowrap"
              >
                {prettifyBucketLabel(param_b, b)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {buckets_a.map((a) => (
            <tr key={a}>
              <td className="border border-border px-2 py-1 text-text-muted font-medium whitespace-nowrap bg-surface">
                {prettifyBucketLabel(param_a, a)}
              </td>
              {buckets_b.map((b) => {
                const cell = cellMap.get(`${a}||${b}`) ?? {
                  bucket_a: a, bucket_b: b, wins: 0, losses: 0, total: 0, win_rate: null,
                };
                return (
                  <CellContent
                    key={b}
                    cell={cell}
                    overall={overall_win_rate}
                    paramA={param_a}
                    paramB={param_b}
                  />
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
