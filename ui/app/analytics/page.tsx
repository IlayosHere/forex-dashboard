"use client";

import { useState, useEffect, useCallback } from "react";

import { StrategyReadinessTable } from "@/components/StrategyReadinessTable";

import type { AnalyticsSummary } from "@/lib/types";

import { strategies } from "@/lib/strategies";
import { fetchAnalyticsSummary } from "@/lib/analyticsApi";

export default function AnalyticsPage() {
  const [summaries, setSummaries] = useState<Map<string, AnalyticsSummary>>(new Map());
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadAll = useCallback(async () => {
    const results = await Promise.allSettled(
      strategies.map((s) => fetchAnalyticsSummary(s.slug))
    );
    const map = new Map<string, AnalyticsSummary>();
    results.forEach((r, i) => {
      if (r.status === "fulfilled") {
        map.set(strategies[i].slug, r.value);
      }
    });
    setSummaries(map);
  }, []);

  useEffect(() => {
    setLoading(true);
    void loadAll().finally(() => setLoading(false));
  }, [loadAll]);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await loadAll();
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div className="p-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-lg font-bold text-text-primary">Analytics</h1>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="px-3 py-1.5 text-sm rounded border border-border bg-surface-input text-text-primary hover:bg-surface-raised disabled:opacity-50"
        >
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      <StrategyReadinessTable summaries={summaries} loading={loading} />
    </div>
  );
}
