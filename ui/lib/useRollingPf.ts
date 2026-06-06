"use client";

import { useState, useEffect, useCallback } from "react";

import type { RollingPfPoint } from "./types";
import type { StatsFiltersParam } from "./api";

import { fetchRollingPf } from "./api";

interface UseRollingPfResult {
  data: RollingPfPoint[];
  loading: boolean;
  error: string | null;
}

export function useRollingPf(filters: StatsFiltersParam = {}): UseRollingPfResult {
  const [data, setData] = useState<RollingPfPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const key = JSON.stringify(filters);

  const load = useCallback(async () => {
    try {
      const result = await fetchRollingPf(filters);
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
