"use client";

import { ContextBar } from "@/components/stats/ContextBar";
import { SectionHeader } from "@/components/stats/SectionHeader";
import { OverviewKpiStrip } from "@/components/stats/OverviewKpiStrip";
import { IctAnalysisSection } from "@/components/stats/IctAnalysisSection";
import { EdgeMetrics } from "@/components/stats/EdgeMetrics";
import { PerformanceBreakdowns } from "@/components/stats/PerformanceBreakdowns";
import { AssessmentAnalysis } from "@/components/stats/AssessmentAnalysis";
import { EquityCurveChart } from "@/components/stats/EquityCurveChart";
import { CalendarHeatmap } from "@/components/stats/CalendarHeatmap";
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

      {isMnq && (
        <section id="ict" className="mb-4">
          <SectionHeader title="ICT Analysis — MNQ Futures" />
          <IctAnalysisSection ictStats={ictData} loading={ictLoading} />
        </section>
      )}

      <section id="edge" className="mb-4">
        <SectionHeader title="Edge Metrics" />
        <EdgeMetrics stats={stats} loading={statsLoading} />
      </section>

      <section id="breakdowns" className="mb-4">
        <SectionHeader title="Performance Breakdowns" />
        <PerformanceBreakdowns stats={stats} loading={statsLoading} />
      </section>

      <section id="assessment" className="mb-4">
        <SectionHeader title="Self-Assessment" subtitle="does confidence predict outcome?" />
        <AssessmentAnalysis
          byConfidence={stats?.by_confidence}
          byRating={stats?.by_rating}
          loading={statsLoading}
        />
      </section>

      <section id="equity" className="mb-4">
        <SectionHeader title="Equity Curve" />
        <EquityCurveChart data={equityData} loading={equityLoading} />
      </section>

      <section id="calendar">
        <SectionHeader title="Calendar" />
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
          <div className="lg:col-span-3">
            <CalendarHeatmap data={dailyData} loading={dailyLoading} />
          </div>
          <div className="lg:col-span-2">
            <MonthlyBars data={dailyData} loading={dailyLoading} />
          </div>
        </div>
      </section>
    </div>
  );
}
