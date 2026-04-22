"use client";

import { useState, useEffect, useCallback, useRef } from "react";

import { StrategyReadinessTable } from "@/components/StrategyReadinessTable";

import type { AnalyticsSummary } from "@/lib/types";

import { strategies } from "@/lib/strategies";
import { fetchAnalyticsSummary } from "@/lib/analyticsApi";

export default function AnalyticsPage() {
  const [summaries, setSummaries] = useState<Map<string, AnalyticsSummary>>(new Map());
  const [loadingSlugs, setLoadingSlugs] = useState<Set<string>>(new Set(strategies.map((s) => s.slug)));
  const [refreshing, setRefreshing] = useState(false);
  const mountedRef = useRef(true);

  const loadAll = useCallback(async (showSkeletons: boolean) => {
    if (showSkeletons) {
      setLoadingSlugs(new Set(strategies.map((s) => s.slug)));
    }

    await Promise.allSettled(
      strategies.map(async (s) => {
        try {
          const data = await fetchAnalyticsSummary(s.slug);
          if (!mountedRef.current) return;
          setSummaries((prev) => {
            const next = new Map(prev);
            next.set(s.slug, data);
            return next;
          });
        } finally {
          if (!mountedRef.current) return;
          setLoadingSlugs((prev) => {
            const next = new Set(prev);
            next.delete(s.slug);
            return next;
          });
        }
      })
    );
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    void loadAll(true);
    return () => { mountedRef.current = false; };
  }, [loadAll]);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await loadAll(false);
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

      <StrategyReadinessTable summaries={summaries} loadingSlugs={loadingSlugs} />
    </div>
  );
}
