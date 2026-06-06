"use client";

import { useState, useEffect, useCallback } from "react";

import type { RollingExpectancyPoint } from "./types";
import type { StatsFiltersParam } from "./api";

import { fetchRollingExpectancy } from "./api";

interface UseRollingExpectancyResult {
  data: RollingExpectancyPoint[];
  loading: boolean;
  error: string | null;
}

export function useRollingExpectancy(
  filters: StatsFiltersParam = {},
  window = 30,
): UseRollingExpectancyResult {
  const [data, setData] = useState<RollingExpectancyPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const key = JSON.stringify({ filters, window });

  const load = useCallback(async () => {
    try {
      const result = await fetchRollingExpectancy(filters, window);
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
