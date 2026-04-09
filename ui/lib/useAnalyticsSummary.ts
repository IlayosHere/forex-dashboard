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

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchAnalyticsSummary(strategy);
      setSummary(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [strategy]);

  useEffect(() => {
    const id = ++cancelRef.current;
    setLoading(true);
    fetchAnalyticsSummary(strategy)
      .then((data) => { if (cancelRef.current === id) { setSummary(data); setError(null); } })
      .catch((e) => { if (cancelRef.current === id) setError(e instanceof Error ? e.message : "Unknown error"); })
      .finally(() => { if (cancelRef.current === id) setLoading(false); });
    return () => { cancelRef.current++; };
  }, [strategy]);

  return { summary, loading, error, refetch: load };
}
