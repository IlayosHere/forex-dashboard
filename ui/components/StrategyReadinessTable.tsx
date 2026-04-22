"use client";

import { useRouter } from "next/navigation";

import { Skeleton } from "@/components/Skeleton";

import type { AnalyticsSummary } from "@/lib/types";

import { SAMPLE_THRESHOLD, formatWinRate } from "@/lib/analyticsFormat";
import { getParamLabel } from "@/lib/analyticsParamMeta";
import { strategies } from "@/lib/strategies";

function winRateColorClass(rate: number): string {
  const pct = rate * 100;
  if (pct >= 55) return "text-bull";
  if (pct <= 45) return "text-bear";
  return "text-text-primary";
}

const COL_CLASSES = "grid grid-cols-[1fr_80px_80px_160px_1fr] gap-4 px-4";

interface StrategyReadinessTableProps {
  summaries: Map<string, AnalyticsSummary>;
  /** Set of strategy slugs still being fetched (skeleton shown for these). */
  loadingSlugs: Set<string>;
}

function SkeletonRow({ slug }: { slug: string }) {
  return (
    <div key={slug} className={`${COL_CLASSES} py-3 border-b border-border bg-card`}>
      <Skeleton className="h-4 w-28" />
      <Skeleton className="h-4 w-8 ml-auto" />
      <Skeleton className="h-4 w-14 ml-auto" />
      <Skeleton className="h-1.5 w-full max-w-[80px] rounded-full" />
      <Skeleton className="h-4 w-32" />
    </div>
  );
}

export function StrategyReadinessTable({ summaries, loadingSlugs }: StrategyReadinessTableProps) {
  const router = useRouter();

  return (
    <div>
      {/* Header */}
      <div className={`${COL_CLASSES} py-2 border-b border-border`}>
        <span className="label">Strategy</span>
        <span className="label text-right">Signals</span>
        <span className="label text-right">Win Rate</span>
        <span className="label">Sample Size</span>
        <span className="label">Top Parameter</span>
      </div>

      {/* Rows */}
      {strategies.map((s) => {
        if (loadingSlugs.has(s.slug)) {
          return <SkeletonRow key={s.slug} slug={s.slug} />;
        }

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
            className={`${COL_CLASSES} py-3 border-b border-border bg-card hover:bg-surface-raised cursor-pointer skeleton-loaded`}
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
                ? getParamLabel(topParam.param_name)
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
