"use client";

import { useMemo } from "react";
import { ContextBar } from "@/components/stats/ContextBar";
import { SectionHeader } from "@/components/stats/SectionHeader";
import { OverviewKpiStrip } from "@/components/stats/OverviewKpiStrip";
import { IctAnalysisSection } from "@/components/stats/IctAnalysisSection";
import { EdgeMetrics } from "@/components/stats/EdgeMetrics";
import { UnifiedBreakdowns } from "@/components/stats/UnifiedBreakdowns";
import { EquityCurveChart } from "@/components/stats/EquityCurveChart";
import { MonthlyBars } from "@/components/stats/MonthlyBars";
import { RDistributionChart } from "@/components/stats/RDistributionChart";
import { DrawdownPanel } from "@/components/stats/DrawdownPanel";
import { LiveDrawdownPanel } from "@/components/stats/LiveDrawdownPanel";
import { RobustnessPanel } from "@/components/stats/RobustnessPanel";
import { RollingExpectancyChart } from "@/components/stats/RollingExpectancyChart";
import { RollingProfitFactor } from "@/components/stats/RollingProfitFactor";

import { useStatsContext } from "@/lib/useStatsContext";
import { useTradeStats } from "@/lib/useTradeStats";
import { useAccounts } from "@/lib/useAccounts";
import { useEquityCurve } from "@/lib/useEquityCurve";
import { useDailySummary } from "@/lib/useDailySummary";
import { useIctStats } from "@/lib/useIctStats";
import { useRollingExpectancy } from "@/lib/useRollingExpectancy";
import { useShowMoney } from "@/lib/useShowMoney";
import { SMALL_SAMPLE_THRESHOLD } from "@/lib/statsHelpers";

export default function StatisticsPage() {
  const ctx = useStatsContext();
  const { accounts } = useAccounts();
  const [showMoney] = useShowMoney();

  const { stats, loading: statsLoading, error, refetch } = useTradeStats(ctx.apiFilters);
  const { data: equityData, loading: equityLoading } = useEquityCurve(ctx.apiFilters);
  const { data: dailyData, loading: dailyLoading } = useDailySummary(ctx.apiFilters);
  const { data: ictData, loading: ictLoading } = useIctStats(ctx.apiFilters);
  const { data: rollingExpectancyData, loading: rollingExpectancyLoading } = useRollingExpectancy(ctx.apiFilters);

  const isMnq = ctx.context.instrumentType?.startsWith("futures") === true;
  const isBacktest = ctx.context.backtestMode;

  const modeFilteredAccounts = useMemo(
    () => accounts.filter((a) =>
      isBacktest ? a.account_type === "backtest" : a.account_type !== "backtest",
    ),
    [accounts, isBacktest],
  );
  const smallSample = !statsLoading && stats != null && stats.closed_trades < SMALL_SAMPLE_THRESHOLD;

  return (
    <div className="p-6">
      <h1 className="text-lg font-semibold text-text-primary mb-4">Statistics</h1>

      <ContextBar ctx={ctx} accounts={modeFilteredAccounts} />

      {error && (
        <div className="mb-4 flex items-center gap-3 rounded border border-bear/30 bg-bear/10 px-4 py-3">
          <p className="text-sm text-bear flex-1">Failed to load statistics: {error}</p>
          <button type="button" onClick={refetch} className="text-sm text-text-primary underline hover:text-white">
            Retry
          </button>
        </div>
      )}

      {isBacktest && smallSample && (
        <div className="mb-4 flex items-center gap-3 rounded border border-amber-400/30 bg-amber-400/10 px-4 py-3">
          <p className="text-xs text-amber-400">
            Small sample — {stats?.closed_trades ?? 0} closed trades. Metrics are unreliable below {SMALL_SAMPLE_THRESHOLD} decisive trades.
          </p>
        </div>
      )}

      <section id="overview" className="mb-4">
        <SectionHeader title="Overview" subtitle={stats ? `${stats.closed_trades} closed trades` : undefined} />
        <OverviewKpiStrip stats={stats} loading={statsLoading} isBacktest={isBacktest} showMoney={showMoney} />
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
        <SectionHeader title={isBacktest ? "Edge Metrics — R-based" : "Edge Metrics"} />
        <EdgeMetrics stats={stats} loading={statsLoading} isBacktest={isBacktest} showMoney={showMoney} />
        {!isBacktest && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-4">
            <RollingExpectancyChart data={rollingExpectancyData} loading={rollingExpectancyLoading} />
            <LiveDrawdownPanel drawdown={stats?.live_drawdown} showMoney={showMoney} />
          </div>
        )}
        {isBacktest && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-4">
            <RDistributionChart distribution={stats?.r_distribution ?? []} />
            <DrawdownPanel drawdown={stats?.drawdown} />
            <RobustnessPanel
              robustness={stats?.robustness}
              expectancy_ci={stats?.expectancy_ci}
              sampleSize={(stats?.wins ?? 0) + (stats?.losses ?? 0)}
            />
            <RollingProfitFactor filters={ctx.apiFilters} />
          </div>
        )}
      </section>

      <hr className="border-border/40" />

      <section id="breakdowns" className="mb-4">
        <SectionHeader title="Performance Breakdowns" />
        <UnifiedBreakdowns stats={stats} ictStats={isMnq ? ictData : null} loading={statsLoading || ictLoading} showMoney={showMoney} isBacktest={isBacktest} />
      </section>

      <hr className="border-border/40" />

      <section id="equity" className="mb-4">
        <SectionHeader title={isBacktest ? "Equity Curve (notional)" : "Equity Curve"} />
        <EquityCurveChart data={equityData} loading={equityLoading} isBacktest={isBacktest} showMoney={showMoney} />
      </section>

      <hr className="border-border/40" />

      <section id="calendar">
        <SectionHeader title={showMoney ? "Monthly P&L" : "Monthly R"} />
        <MonthlyBars data={dailyData} loading={dailyLoading} isBacktest={isBacktest} showMoney={showMoney} />
      </section>
    </div>
  );
}
