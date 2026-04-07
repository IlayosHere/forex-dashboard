"use client";

import { useState, useMemo } from "react";

import { StatsFilters } from "@/components/StatsFilters";
import { AccountStatsStrip } from "@/components/AccountStatsStrip";
import { EquityCurveChart } from "@/components/stats/EquityCurveChart";
import { CalendarHeatmap } from "@/components/stats/CalendarHeatmap";
import { MonthlyBars } from "@/components/stats/MonthlyBars";
import { PerformanceBreakdowns } from "@/components/stats/PerformanceBreakdowns";
import { EdgeMetrics } from "@/components/stats/EdgeMetrics";
import { AssessmentAnalysis } from "@/components/stats/AssessmentAnalysis";

import type { InstrumentType } from "@/lib/types";

import { useTradeStats } from "@/lib/useTradeStats";
import { useAccounts } from "@/lib/useAccounts";
import { useEquityCurve } from "@/lib/useEquityCurve";
import { useDailySummary } from "@/lib/useDailySummary";

type PresetKey = "7d" | "30d" | "month" | "3m" | "all";

const PRESETS: { key: PresetKey; label: string }[] = [
  { key: "7d", label: "Last 7 Days" },
  { key: "30d", label: "Last 30 Days" },
  { key: "month", label: "This Month" },
  { key: "3m", label: "Last 3 Months" },
  { key: "all", label: "All Time" },
];

function computePresetDates(preset: PresetKey): { from: string; to: string } {
  const now = new Date();
  const to = now.toISOString().slice(0, 10);
  if (preset === "all") return { from: "", to: "" };
  if (preset === "month") {
    const from = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
    return { from, to };
  }
  const days = preset === "7d" ? 7 : preset === "30d" ? 30 : 90;
  const fromDate = new Date(now);
  fromDate.setDate(fromDate.getDate() - days);
  return { from: fromDate.toISOString().slice(0, 10), to };
}

export default function StatisticsPage() {
  const [instrumentType, setInstrumentType] = useState<InstrumentType | "">("");
  const [strategy, setStrategy] = useState("");
  const [accountId, setAccountId] = useState("");
  const [preset, setPreset] = useState<PresetKey>("all");
  const [customFrom, setCustomFrom] = useState("");
  const [customTo, setCustomTo] = useState("");

  const { accounts } = useAccounts();

  const dates = useMemo(() => {
    if (customFrom || customTo) return { from: customFrom, to: customTo };
    return computePresetDates(preset);
  }, [preset, customFrom, customTo]);

  const apiFilters = useMemo(() => {
    const f: Record<string, string | undefined> = {};
    if (instrumentType) f.instrument_type = instrumentType;
    if (strategy) f.strategy = strategy;
    if (accountId) f.account_id = accountId;
    if (dates.from) f.from = dates.from;
    if (dates.to) f.to = dates.to;
    return f;
  }, [instrumentType, strategy, accountId, dates]);

  const { stats, loading: statsLoading, error, refetch } = useTradeStats(apiFilters);
  const { data: equityData, loading: equityLoading } = useEquityCurve(apiFilters);
  const { data: dailyData, loading: dailyLoading } = useDailySummary(apiFilters);

  function handlePresetChange(value: string) {
    setPreset(value as PresetKey);
    setCustomFrom("");
    setCustomTo("");
  }

  function handleFromChange(v: string) {
    setCustomFrom(v);
    if (v) setPreset("all");
  }

  function handleToChange(v: string) {
    setCustomTo(v);
    if (v) setPreset("all");
  }

  return (
    <div className="p-6 max-w-7xl">
      <h1 className="text-lg font-semibold text-text-primary mb-4">Statistics</h1>

      {/* Filters */}
      <StatsFilters
        instrumentType={instrumentType}
        onInstrumentChange={setInstrumentType}
        strategy={strategy}
        onStrategyChange={setStrategy}
        accountId={accountId}
        onAccountChange={setAccountId}
        accounts={accounts}
        from={customFrom}
        onFromChange={handleFromChange}
        to={customTo}
        onToChange={handleToChange}
      />

      {/* Preset selector */}
      <div className="flex gap-2 mb-4">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            type="button"
            onClick={() => handlePresetChange(p.key)}
            className={`px-3 py-1 text-xs rounded-full border ${
              preset === p.key && !customFrom && !customTo
                ? "border-bull text-bull bg-bull/10"
                : "border-border text-text-muted hover:text-text-primary"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* Account strip */}
      <AccountStatsStrip
        byAccount={stats?.by_account ?? {}}
        selectedAccountId={accountId}
        onSelect={setAccountId}
        loading={statsLoading}
      />

      {error && (
        <div className="mb-4 flex items-center gap-3 rounded border border-bear/30 bg-bear/10 px-4 py-3">
          <p className="text-sm text-bear flex-1">Failed to load statistics: {error}</p>
          <button type="button" onClick={refetch} className="text-sm text-text-primary underline hover:text-white">
            Retry
          </button>
        </div>
      )}

      {/* Section 1: Equity Curve */}
      <EquityCurveChart data={equityData} stats={stats} loading={equityLoading || statsLoading} />

      {/* Section 2: Calendar + Monthly */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3 mt-3">
        <div className="lg:col-span-3">
          <CalendarHeatmap data={dailyData} loading={dailyLoading} />
        </div>
        <div className="lg:col-span-2">
          <MonthlyBars data={dailyData} loading={dailyLoading} />
        </div>
      </div>

      {/* Section 3: Performance Breakdowns */}
      <div className="mt-3">
        <PerformanceBreakdowns stats={stats} loading={statsLoading} />
      </div>

      {/* Section 4: Edge Metrics */}
      <div className="mt-3">
        <EdgeMetrics stats={stats} loading={statsLoading} />
      </div>

      {/* Section 5: Assessment Analysis */}
      <div className="mt-3">
        <AssessmentAnalysis
          byConfidence={stats?.by_confidence}
          byRating={stats?.by_rating}
          loading={statsLoading}
        />
      </div>
    </div>
  );
}
