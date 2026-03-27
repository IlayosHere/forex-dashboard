"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchTrades, type TradeFilters } from "./api";
import type { Trade } from "./types";

interface UseTradesResult {
  trades: Trade[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useTrades(filters: TradeFilters = {}): UseTradesResult {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const key = JSON.stringify(filters);

  const load = useCallback(async () => {
    try {
      const data = await fetchTrades(filters);
      // Hide cancelled trades unless explicitly filtering for them
      const filtered = filters.status
        ? data
        : data.filter((t) => t.status !== "cancelled");
      setTrades(filtered);
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
    const interval = setInterval(() => { void load(); }, 30_000);
    return () => clearInterval(interval);
  }, [load]);

  return { trades, loading, error, refetch: load };
}
