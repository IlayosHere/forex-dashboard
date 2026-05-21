import type { GatePreviewResponse, GateCondition } from "@/lib/gatesTypes";

interface GatePreviewPanelProps {
  preview: GatePreviewResponse;
  conditions: GateCondition[];
}

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

function deltaColor(delta: number | null): string {
  if (delta === null) return "text-muted-foreground";
  return delta > 0 ? "text-bull" : delta < 0 ? "text-bear" : "text-muted-foreground";
}

export function GatePreviewPanel({ preview, conditions }: GatePreviewPanelProps) {
  const delta = preview.delta_vs_baseline;

  return (
    <div
      className="rounded border border-border bg-surface p-3 space-y-3 text-xs"
      aria-label="Gate preview results"
    >
      <div className="flex items-center gap-1 text-muted-foreground font-medium uppercase tracking-wide text-[10px]">
        Preview
      </div>

      <div className="grid grid-cols-3 gap-3">
        <div>
          <div className="text-muted-foreground mb-0.5">Pass rate</div>
          <div className="font-semibold text-foreground">{pct(preview.pass_rate)}</div>
          <div className="text-muted-foreground text-[10px]">{preview.pass_count} / {preview.total_signals_evaluated}</div>
        </div>

        <div>
          <div className="text-muted-foreground mb-0.5">Win rate (passed)</div>
          <div className="font-semibold text-foreground">
            {preview.win_rate_passed !== null ? pct(preview.win_rate_passed) : "—"}
          </div>
          <div className="text-muted-foreground text-[10px]">
            baseline {preview.win_rate_baseline !== null ? pct(preview.win_rate_baseline) : "—"}
          </div>
        </div>

        <div>
          <div className="text-muted-foreground mb-0.5">Delta</div>
          <div className={`font-semibold ${deltaColor(delta)}`}>
            {delta !== null ? `${delta > 0 ? "+" : ""}${pct(delta)}` : "—"}
          </div>
        </div>
      </div>

      {conditions.length > 0 && preview.per_condition_failure_count.length > 0 && (
        <div className="space-y-1">
          <div className="text-muted-foreground text-[10px] uppercase tracking-wide">Blocked by condition</div>
          {conditions.map((cond, i) => {
            const count = preview.per_condition_failure_count[i] ?? 0;
            const pctBlocked = preview.total_signals_evaluated > 0
              ? (count / preview.total_signals_evaluated) * 100
              : 0;
            return (
              <div key={i} className="flex items-center gap-2">
                <span className="text-muted-foreground w-32 truncate">{cond.param}</span>
                <div className="flex-1 bg-border rounded-full h-1">
                  <div
                    className="bg-bear/60 h-1 rounded-full"
                    style={{ width: `${Math.min(100, pctBlocked)}%` }}
                    aria-label={`${count} blocked`}
                  />
                </div>
                <span className="text-muted-foreground w-8 text-right">{count}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
