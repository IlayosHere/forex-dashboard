"use client";

import { useRouter } from "next/navigation";

import type { AnalyticsSummary } from "@/lib/types";

import { strategies } from "@/lib/strategies";

const SAMPLE_THRESHOLD = 150;

function formatWinRate(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

function winRateColorClass(rate: number): string {
  const pct = rate * 100;
  if (pct >= 55) return "text-bull";
  if (pct <= 45) return "text-bear";
  return "text-text-primary";
}

interface StrategyReadinessTableProps {
  summaries: Map<string, AnalyticsSummary>;
  loading: boolean;
}

export function StrategyReadinessTable({ summaries, loading }: StrategyReadinessTableProps) {
  const router = useRouter();
  const dim = loading ? "opacity-50" : "";

  return (
    <div className={dim}>
      {/* Header */}
      <div className="grid grid-cols-[1fr_80px_80px_160px_1fr] gap-4 px-4 py-2 border-b border-border">
        <span className="label">Strategy</span>
        <span className="label text-right">Signals</span>
        <span className="label text-right">Win Rate</span>
        <span className="label">Sample Size</span>
        <span className="label">Top Parameter</span>
      </div>

      {/* Rows */}
      {strategies.map((s) => {
        const summary = summaries.get(s.slug);
        const resolved = summary?.total_resolved ?? 0;
        const winRate = summary?.win_rate_overall ?? 0;
        const topParam = summary?.top_correlations.find((c) => c.significant);
        const pct = Math.min((resolved / SAMPLE_THRESHOLD) * 100, 100);

        return (
          <div
            key={s.slug}
            data-interactive
            role="button"
            tabIndex={0}
            onClick={() => router.push(`/analytics/${s.slug}`)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                router.push(`/analytics/${s.slug}`);
              }
            }}
            className="grid grid-cols-[1fr_80px_80px_160px_1fr] gap-4 px-4 py-3 border-b border-border bg-card hover:bg-surface-raised cursor-pointer"
          >
            <span className="font-bold text-text-primary">{s.label}</span>
            <span className="text-right tabular-nums text-text-primary">{resolved}</span>
            <span className={`text-right tabular-nums font-semibold ${winRateColorClass(winRate)}`}>
              {resolved > 0 ? formatWinRate(winRate) : "—"}
            </span>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 rounded-full bg-elevated overflow-hidden max-w-[80px]">
                <div
                  className="h-full rounded-full bg-accent-gold"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-xs tabular-nums text-text-muted">{resolved}/{SAMPLE_THRESHOLD}</span>
            </div>
            <span className={resolved >= SAMPLE_THRESHOLD && topParam ? "text-text-primary" : "text-text-dim"}>
              {resolved >= SAMPLE_THRESHOLD && topParam
                ? topParam.param_name
                : resolved > 0
                  ? "Need 150+ signals"
                  : "No data"}
            </span>
          </div>
        );
      })}
    </div>
  );
}
