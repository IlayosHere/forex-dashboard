"use client";

import { ContextBar } from "@/components/stats/ContextBar";
import { SectionHeader } from "@/components/stats/SectionHeader";
import { OverviewKpiStrip } from "@/components/stats/OverviewKpiStrip";
import { IctAnalysisSection } from "@/components/stats/IctAnalysisSection";
import { EdgeMetrics } from "@/components/stats/EdgeMetrics";
import { UnifiedBreakdowns } from "@/components/stats/UnifiedBreakdowns";
import { EquityCurveChart } from "@/components/stats/EquityCurveChart";
import { MonthlyBars } from "@/components/stats/MonthlyBars";

import { useStatsContext } from "@/lib/useStatsContext";
import { useTradeStats } from "@/lib/useTradeStats";
import { useAccounts } from "@/lib/useAccounts";
import { useEquityCurve } from "@/lib/useEquityCurve";
import { useDailySummary } from "@/lib/useDailySummary";
import { useIctStats } from "@/lib/useIctStats";

export default function StatisticsPage() {
  const ctx = useStatsContext();
  const { accounts } = useAccounts();

  const { stats, loading: statsLoading, error, refetch } = useTradeStats(ctx.apiFilters);
  const { data: equityData, loading: equityLoading } = useEquityCurve(ctx.apiFilters);
  const { data: dailyData, loading: dailyLoading } = useDailySummary(ctx.apiFilters);
  const { data: ictData, loading: ictLoading } = useIctStats(ctx.apiFilters);

  const isMnq = ctx.context.instrumentType === "futures_mnq";

  return (
    <div className="p-6 max-w-7xl">
      <h1 className="text-lg font-semibold text-text-primary mb-4">Statistics</h1>

      <ContextBar ctx={ctx} accounts={accounts} />

      {error && (
        <div className="mb-4 flex items-center gap-3 rounded border border-bear/30 bg-bear/10 px-4 py-3">
          <p className="text-sm text-bear flex-1">Failed to load statistics: {error}</p>
          <button type="button" onClick={refetch} className="text-sm text-text-primary underline hover:text-white">
            Retry
          </button>
        </div>
      )}

      <section id="overview" className="mb-4">
        <SectionHeader title="Overview" subtitle={stats ? `${stats.closed_trades} closed trades` : undefined} />
        <OverviewKpiStrip stats={stats} loading={statsLoading} />
      </section>

      <hr className="border-border/40" />

      {isMnq && (
        <>
          <section id="ict" className="mb-4">
            <SectionHeader title="ICT Analysis — MNQ Futures" />
            <IctAnalysisSection ictStats={ictData} loading={ictLoading} />
          </section>
          <hr className="border-border/40" />
        </>
      )}

      <section id="edge" className="mb-4">
        <SectionHeader title="Edge Metrics" />
        <EdgeMetrics stats={stats} loading={statsLoading} />
      </section>

      <hr className="border-border/40" />

      <section id="breakdowns" className="mb-4">
        <SectionHeader title="Performance Breakdowns" />
        <UnifiedBreakdowns stats={stats} ictStats={isMnq ? ictData : null} loading={statsLoading || ictLoading} />
      </section>

      <hr className="border-border/40" />

      <section id="equity" className="mb-4">
        <SectionHeader title="Equity Curve" />
        <EquityCurveChart data={equityData} loading={equityLoading} />
      </section>

      <hr className="border-border/40" />

      <section id="calendar">
        <SectionHeader title="Monthly P&amp;L" />
        <MonthlyBars data={dailyData} loading={dailyLoading} />
      </section>
    </div>
  );
}
