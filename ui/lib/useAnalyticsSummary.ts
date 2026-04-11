"use client";

import { useState, useEffect, useCallback, useRef } from "react";

import type { AnalyticsSummary } from "./types";

import { fetchAnalyticsSummary } from "./analyticsApi";

export interface UseAnalyticsSummaryResult {
  summary: AnalyticsSummary | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useAnalyticsSummary(strategy: string): UseAnalyticsSummaryResult {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);

  // Single fetch path used by both the initial effect and manual refetch.
  // Owns the cancelRef stale-request guard so concurrent calls cannot race.
  const load = useCallback(async () => {
    const id = ++cancelRef.current;
    setLoading(true);
    try {
      const data = await fetchAnalyticsSummary(strategy);
      if (cancelRef.current !== id) return;
      setSummary(data);
      setError(null);
    } catch (e) {
      if (cancelRef.current !== id) return;
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      if (cancelRef.current === id) setLoading(false);
    }
  }, [strategy]);

  useEffect(() => {
    load();
    // Cancel any in-flight request when strategy changes or component unmounts.
    return () => { cancelRef.current++; };
  }, [load]);

  return { summary, loading, error, refetch: load };
}
