"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchTradeStats } from "./api";
import type { TradeStats } from "./types";

interface UseTradeStatsResult {
  stats: TradeStats | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useTradeStats(filters: { strategy?: string; symbol?: string; from?: string; to?: string } = {}): UseTradeStatsResult {
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const key = JSON.stringify(filters);

  const load = useCallback(async () => {
    try {
      const data = await fetchTradeStats(filters);
      setStats(data);
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

  return { stats, loading, error, refetch: load };
}
