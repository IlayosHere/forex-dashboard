import type { ExperimentResult } from "@/lib/gatesTypes";

interface ExperimentResultPanelProps {
  result: ExperimentResult;
}

function pct(n: number | null): string {
  if (n === null) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function deltaDisplay(delta: number | null): { text: string; cls: string } {
  if (delta === null) return { text: "—", cls: "text-muted-foreground" };
  const sign = delta > 0 ? "▲" : delta < 0 ? "▼" : "";
  const cls = delta > 0 ? "text-bull" : delta < 0 ? "text-bear" : "text-muted-foreground";
  return { text: `${sign} ${pct(delta)}`, cls };
}

export function ExperimentResultPanel({ result }: ExperimentResultPanelProps) {
  const { text: dText, cls: dCls } = deltaDisplay(result.delta_vs_baseline);

  return (
    <div className="space-y-4 rounded border border-border bg-surface p-4 text-sm">
      <div className="grid grid-cols-2 gap-6">
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Baseline win rate</div>
          <div className="text-2xl font-bold text-foreground tabular-nums">{pct(result.win_rate_baseline)}</div>
          <div className="text-xs text-muted-foreground mt-0.5">{result.resolved_signals} resolved signals</div>
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground mb-1">Filtered win rate</div>
          <div className="text-2xl font-bold text-foreground tabular-nums">{pct(result.win_rate_passed)}</div>
          <div className={`text-xs font-semibold mt-0.5 ${dCls}`}>{dText} vs baseline</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 text-xs border-t border-border pt-3">
        <div>
          <div className="text-muted-foreground mb-0.5">Total signals</div>
          <div className="font-semibold text-foreground">{result.total_signals}</div>
        </div>
        <div>
          <div className="text-muted-foreground mb-0.5">Passing signals</div>
          <div className="font-semibold text-foreground">{result.passing_signals}</div>
        </div>
        <div>
          <div className="text-muted-foreground mb-0.5">Resolved (passing)</div>
          <div className="font-semibold text-foreground">{result.resolved_passing}</div>
        </div>
      </div>

      {result.per_param_breakdown.length > 0 && (
        <div className="space-y-3 border-t border-border pt-3">
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground">Parameter breakdown</div>
          {result.per_param_breakdown.map((param) => (
            <div key={param.param_name} className="space-y-1.5">
              <div className="text-xs font-medium text-foreground">{param.param_name}</div>
              <div className="space-y-1">
                {param.buckets.map((bucket) => {
                  const barWidth = Math.min(100, bucket.win_rate * 100);
                  return (
                    <div key={bucket.bucket} className="flex items-center gap-2 text-xs">
                      <span className="text-muted-foreground w-24 truncate text-[10px]">{bucket.bucket}</span>
                      <div className="flex-1 bg-border rounded-full h-1.5">
                        <div
                          className="bg-bull/70 h-1.5 rounded-full"
                          style={{ width: `${barWidth}%` }}
                          aria-label={`${bucket.bucket}: ${pct(bucket.win_rate)}`}
                        />
                      </div>
                      <span className="text-foreground tabular-nums w-12 text-right">{pct(bucket.win_rate)}</span>
                      <span className="text-muted-foreground w-8 text-right text-[10px]">n={bucket.n}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
