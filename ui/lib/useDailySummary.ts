"use client";

import { useState, useEffect, useCallback } from "react";

import type { DailySummaryPoint } from "./types";
import type { StatsFiltersParam } from "./api";

import { fetchDailySummary } from "./api";

interface UseDailySummaryResult {
  data: DailySummaryPoint[];
  loading: boolean;
  error: string | null;
}

export function useDailySummary(filters: StatsFiltersParam = {}): UseDailySummaryResult {
  const [data, setData] = useState<DailySummaryPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const key = JSON.stringify(filters);

  const load = useCallback(async () => {
    try {
      const result = await fetchDailySummary(filters);
      setData(result);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    setLoading(true);
    void load();
  }, [load]);

  return { data, loading, error };
}
