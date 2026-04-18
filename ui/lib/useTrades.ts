"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { fetchTrades, type TradeFilters } from "./api";
import type { Trade } from "./types";

const POLL_INTERVAL_MS = 30_000;

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
  const cancelRef = useRef(0);

  const key = JSON.stringify(filters);

  const load = useCallback(async () => {
    const id = ++cancelRef.current;
    const parsedFilters = JSON.parse(key) as TradeFilters;
    try {
      const data = await fetchTrades(parsedFilters);
      if (cancelRef.current !== id) return;
      // Hide cancelled trades unless explicitly filtering for them
      const filtered = parsedFilters.status
        ? data
        : data.filter((t) => t.status !== "cancelled");
      setTrades(filtered);
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
    const interval = setInterval(() => { void load(); }, POLL_INTERVAL_MS);
    return () => {
      cancelRef.current++;
      clearInterval(interval);
    };
  }, [load]);

  return { trades, loading, error, refetch: load };
}
