"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { fetchTradeStats } from "./api";
import type { TradeStats } from "./types";

interface UseTradeStatsResult {
  stats: TradeStats | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useTradeStats(filters: { strategy?: string; symbol?: string; from?: string; to?: string; instrument_type?: string; account_id?: string } = {}): UseTradeStatsResult {
  const [stats, setStats] = useState<TradeStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);

  const key = JSON.stringify(filters);

  const load = useCallback(async () => {
    const id = ++cancelRef.current;
    try {
      const data = await fetchTradeStats(JSON.parse(key) as typeof filters);
      if (cancelRef.current !== id) return;
      setStats(data);
      setError(null);
    } catch (e) {
      if (cancelRef.current !== id) return;
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      if (cancelRef.current === id) setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    setLoading(true);
    void load();
    const interval = setInterval(() => { void load(); }, 30_000);
    return () => {
      cancelRef.current++;
      clearInterval(interval);
    };
  }, [load]);

  return { stats, loading, error, refetch: load };
}
