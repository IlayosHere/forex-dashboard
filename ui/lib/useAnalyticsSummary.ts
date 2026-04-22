"use client";

import { useState, useEffect, useCallback, useRef } from "react";

import type { AnalyticsSummary } from "./types";

import { fetchAnalyticsSummary } from "./analyticsApi";

export interface UseAnalyticsSummaryResult {
  summary: AnalyticsSummary | null;
  /** True only on initial load (no prior data). Use for skeleton display. */
  loading: boolean;
  /** True during a background refresh (prior data remains visible). */
  refreshing: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useAnalyticsSummary(strategy: string): UseAnalyticsSummaryResult {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);
  const hasDataRef = useRef(false);

  const load = useCallback(async () => {
    const id = ++cancelRef.current;
    if (hasDataRef.current) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    try {
      const data = await fetchAnalyticsSummary(strategy);
      if (cancelRef.current !== id) return;
      setSummary(data);
      setError(null);
      hasDataRef.current = true;
    } catch (e) {
      if (cancelRef.current !== id) return;
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      if (cancelRef.current === id) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [strategy]);

  useEffect(() => {
    hasDataRef.current = false;
    load();
    return () => { cancelRef.current++; };
  }, [load]);

  return { summary, loading, refreshing, error, refetch: load };
}
