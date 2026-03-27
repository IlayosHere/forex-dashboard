"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchSignals, type SignalFilters } from "./api";
import type { Signal } from "./types";

interface UseSignalsResult {
  signals: Signal[];
  total: number;
  loading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}

export function useSignals(filters: SignalFilters = {}): UseSignalsResult {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Serialize filters to a stable string for dependency tracking
  const filterKey = JSON.stringify(filters);

  const load = useCallback(async () => {
    try {
      const data = await fetchSignals(JSON.parse(filterKey) as SignalFilters);
      setSignals(data.items);
      setTotal(data.total);
      setLastUpdated(new Date());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [filterKey]);

  useEffect(() => {
    setLoading(true);
    void load();
    const interval = setInterval(() => { void load(); }, 30_000);
    return () => clearInterval(interval);
  }, [load]);

  return { signals, total, loading, error, lastUpdated };
}
