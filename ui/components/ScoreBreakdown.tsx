"use client";

import { getParamLabel } from "@/lib/analyticsParamMeta";

import type { ScoreContributor, ScoreResponse } from "@/lib/types";

interface ScoreBreakdownProps {
  scoreData: ScoreResponse;
}

function ScoreHeader({ score, maxPossible }: { score: number; maxPossible: number }) {
  const sign = score > 0 ? "+" : "";
  const color =
    score > 0 ? "text-bull" : score < 0 ? "text-bear" : "text-muted-foreground";
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        Setup Quality
      </span>
      <span className={`text-sm font-bold tabular-nums ${color}`}>
        {sign}{score} / {maxPossible}
      </span>
    </div>
  );
}

function ContributorRow({ c }: { c: ScoreContributor }) {
  const label = getParamLabel(c.param_name);
  const bucketLabel = c.bucket ?? "—";

  if (c.indicator === 1) {
    return (
      <div className="flex items-start justify-between gap-2 text-xs">
        <span className="text-bull flex items-center gap-1 min-w-0">
          <span className="shrink-0">✓</span>
          <span className="truncate">{label} — {bucketLabel}</span>
        </span>
        <span className="text-bull shrink-0 tabular-nums">+{c.weight}</span>
      </div>
    );
  }
  if (c.indicator === -1) {
    return (
      <div className="flex items-start justify-between gap-2 text-xs">
        <span className="text-bear flex items-center gap-1 min-w-0">
          <span className="shrink-0">✗</span>
          <span className="truncate">{label} — {bucketLabel}</span>
        </span>
        <span className="text-bear shrink-0 tabular-nums">−{c.weight}</span>
      </div>
    );
  }
  return (
    <div className="flex items-start gap-1 text-xs text-muted-foreground">
      <span className="shrink-0">·</span>
      <span className="truncate">{label} — {bucketLabel}</span>
    </div>
  );
}

export function ScoreBreakdown({ scoreData }: ScoreBreakdownProps) {
  if (scoreData.max_possible === 0) return null;

  const matched = scoreData.contributing.filter((c) => c.indicator === 1);
  const violated = scoreData.contributing.filter((c) => c.indicator === -1);
  const neutral = scoreData.contributing.filter((c) => c.indicator === 0);

  return (
    <div className="border border-border rounded px-3 py-2.5 bg-card space-y-2.5">
      <ScoreHeader score={scoreData.score} maxPossible={scoreData.max_possible} />
      {matched.length > 0 && (
        <div className="space-y-1">
          {matched.map((c) => <ContributorRow key={c.param_name} c={c} />)}
        </div>
      )}
      {violated.length > 0 && (
        <div className="space-y-1 pt-1 border-t border-border/50">
          {violated.map((c) => <ContributorRow key={c.param_name} c={c} />)}
        </div>
      )}
      {neutral.length > 0 && (
        <div className="space-y-1 pt-1 border-t border-border/50">
          {neutral.map((c) => <ContributorRow key={c.param_name} c={c} />)}
        </div>
      )}
    </div>
  );
}
