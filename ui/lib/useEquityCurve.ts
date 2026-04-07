"use client";

import { useState, useEffect, useCallback } from "react";

import type { EquityCurvePoint } from "./types";
import type { StatsFiltersParam } from "./api";

import { fetchEquityCurve } from "./api";

interface UseEquityCurveResult {
  data: EquityCurvePoint[];
  loading: boolean;
  error: string | null;
}

export function useEquityCurve(filters: StatsFiltersParam = {}): UseEquityCurveResult {
  const [data, setData] = useState<EquityCurvePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const key = JSON.stringify(filters);

  const load = useCallback(async () => {
    try {
      const result = await fetchEquityCurve(filters);
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
