"use client";

import { useState, useEffect, useCallback } from "react";

import { fetchIctStats } from "./api";

import type { IctStatsResponse } from "./ictTypes";
import type { StatsFiltersParam } from "./api";

const POLL_INTERVAL_MS = 30_000;

interface UseIctStatsResult {
  data: IctStatsResponse | null;
  loading: boolean;
  error: string | null;
}

export function useIctStats(filters: StatsFiltersParam = {}): UseIctStatsResult {
  const [data, setData] = useState<IctStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const key = JSON.stringify(filters);

  const load = useCallback(async () => {
    try {
      const result = await fetchIctStats(filters);
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
    const interval = setInterval(() => { void load(); }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [load]);

  return { data, loading, error };
}
