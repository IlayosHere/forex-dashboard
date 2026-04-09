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

  const load = useCallback(async () => {
    if (!paramName) return;
    setLoading(true);
    try {
      const data = await fetchUnivariateReport(paramName, strategy);
      setReport(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [paramName, strategy]);

  useEffect(() => {
    if (!paramName) {
      setReport(null);
      return;
    }
    const id = ++cancelRef.current;
    setLoading(true);
    fetchUnivariateReport(paramName, strategy)
      .then((data) => { if (cancelRef.current === id) { setReport(data); setError(null); } })
      .catch((e) => { if (cancelRef.current === id) setError(e instanceof Error ? e.message : "Unknown error"); })
      .finally(() => { if (cancelRef.current === id) setLoading(false); });
    return () => { cancelRef.current++; };
  }, [paramName, strategy]);

  return { report, loading, error, refetch: load };
}
