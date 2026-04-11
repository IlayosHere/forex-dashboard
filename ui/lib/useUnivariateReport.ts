"use client";

import { useState, useEffect, useCallback, useRef } from "react";

import type { UnivariateReport } from "./types";

import { fetchUnivariateReport } from "./analyticsApi";

export interface UseUnivariateReportResult {
  report: UnivariateReport | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useUnivariateReport(
  paramName: string | null,
  strategy: string
): UseUnivariateReportResult {
  const [report, setReport] = useState<UnivariateReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);

  // Single fetch path used by both the initial effect and manual refetch.
  // Owns the cancelRef stale-request guard so concurrent calls cannot race.
  const load = useCallback(async () => {
    if (!paramName) {
      setReport(null);
      return;
    }
    const id = ++cancelRef.current;
    setLoading(true);
    try {
      const data = await fetchUnivariateReport(paramName, strategy);
      if (cancelRef.current !== id) return;
      setReport(data);
      setError(null);
    } catch (e) {
      if (cancelRef.current !== id) return;
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      if (cancelRef.current === id) setLoading(false);
    }
  }, [paramName, strategy]);

  useEffect(() => {
    load();
    // Cancel any in-flight request when paramName/strategy changes or component unmounts.
    return () => { cancelRef.current++; };
  }, [load]);

  return { report, loading, error, refetch: load };
}
