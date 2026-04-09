"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";

import { ParamRankingTable } from "@/components/ParamRankingTable";
import { SampleSizeNotice } from "@/components/SampleSizeNotice";
import { WinRateBuckets } from "@/components/WinRateBuckets";

import { strategies } from "@/lib/strategies";
import { useAnalyticsSummary } from "@/lib/useAnalyticsSummary";
import { useUnivariateReport } from "@/lib/useUnivariateReport";

const SAMPLE_THRESHOLD = 150;

function formatWinRate(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

export default function AnalyticsStrategyPage() {
  const params = useParams<{ strategy: string }>();
  const router = useRouter();
  const slug = params.strategy;
  const meta = strategies.find((s) => s.slug === slug);
  const strategyLabel = meta?.label ?? slug;

  const { summary, loading, refetch } = useAnalyticsSummary(slug);
  const [selectedParam, setSelectedParam] = useState<string | null>(null);
  const { report, loading: reportLoading, error: reportError } = useUnivariateReport(selectedParam, slug);
  const [refreshing, setRefreshing] = useState(false);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await refetch();
    } finally {
      setRefreshing(false);
    }
  }

  const resolved = summary?.total_resolved ?? 0;
  const winRate = summary?.win_rate_overall ?? 0;
  const correlations = summary?.top_correlations ?? [];

  return (
    <div className="p-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/analytics")}
            className="text-text-muted hover:text-text-primary text-sm"
          >
            &larr; Analytics
          </button>
          <span className="text-text-dim">/</span>
          <h1 className="text-lg font-bold text-text-primary">{strategyLabel}</h1>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing || loading}
          className="px-3 py-1.5 text-sm rounded border border-border bg-surface-input text-text-primary hover:bg-surface-raised disabled:opacity-50"
        >
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* Stats row */}
      <div className={`flex gap-3 overflow-x-auto pb-1 mb-4 ${loading ? "opacity-50" : ""}`}>
        <StatCard title="Resolved Signals" value={String(resolved)} />
        <StatCard
          title="Win Rate"
          value={resolved > 0 ? formatWinRate(winRate) : "—"}
          colorClass={
            winRate * 100 >= 55
              ? "text-bull"
              : winRate * 100 <= 45
                ? "text-bear"
                : "text-text-primary"
          }
        />
        <StatCard title="Params Analyzed" value={String(summary?.params_analyzed ?? 0)} />
      </div>

      {/* Sample size notice */}
      {resolved > 0 && resolved < SAMPLE_THRESHOLD && (
        <div className="mb-4">
          <SampleSizeNotice count={resolved} />
        </div>
      )}

      {/* Parameter ranking */}
      <div className="mb-2">
        <span className="label px-4">Parameter Ranking</span>
      </div>
      <div className="mb-6">
        <ParamRankingTable
          correlations={correlations}
          selectedParam={selectedParam}
          onSelectParam={setSelectedParam}
        />
      </div>

      {/* Bucket chart */}
      {selectedParam ? (
        <div className="border border-border rounded bg-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <span className="label">Win Rate by Bucket:</span>
            <span className="text-sm font-medium text-text-primary">{selectedParam}</span>
          </div>
          {reportError ? (
            <div className="py-8 text-center text-destructive text-sm">
              Failed to load data for {selectedParam}
            </div>
          ) : report ? (
            <WinRateBuckets
              report={report}
              overallWinRate={winRate}
              loading={reportLoading}
            />
          ) : reportLoading ? (
            <div className="py-8 text-center text-text-muted text-sm opacity-50">
              Loading...
            </div>
          ) : null}
        </div>
      ) : (
        <div className="border border-dashed border-border rounded min-h-[200px] flex items-center justify-center">
          <span className="text-text-muted text-sm">
            Select a parameter above to view win rate breakdown
          </span>
        </div>
      )}
    </div>
  );
}

function StatCard({
  title,
  value,
  colorClass,
}: {
  title: string;
  value: string;
  colorClass?: string;
}) {
  return (
    <div className="shrink-0 border border-border rounded px-4 py-3 min-w-[120px] bg-card">
      <div className="label mb-1">{title}</div>
      <div className={`text-lg font-bold tabular-nums ${colorClass ?? "text-text-primary"}`}>
        {value}
      </div>
    </div>
  );
}
