"use client";

import { useState, useEffect, useCallback, useRef } from "react";

import { fetchMarketHolidays } from "@/lib/api";
import type { MarketClosure } from "@/lib/types";

// Holiday data is static/offline — polling matches the calendar's cadence for
// a uniform refresh model, not because this data actually changes that often.
const POLL_INTERVAL_MS = 5 * 60 * 1000;

export interface UseMarketHolidaysResult {
  closures: MarketClosure[];
  loading: boolean;
  error: string | null;
}

interface UseMarketHolidaysOptions {
  week: "current" | "next";
}

export function useMarketHolidays({ week }: UseMarketHolidaysOptions): UseMarketHolidaysResult {
  const [closures, setClosures] = useState<MarketClosure[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);

  const loadData = useCallback(async () => {
    const id = ++cancelRef.current;
    try {
      const data = await fetchMarketHolidays(week);
      if (cancelRef.current !== id) return;
      setClosures(data);
      setError(null);
    } catch (err) {
      if (cancelRef.current !== id) return;
      setError(err instanceof Error ? err.message : "Failed to load market holidays");
    } finally {
      if (cancelRef.current === id) setLoading(false);
    }
  }, [week]);

  useEffect(() => {
    setLoading(true);
    void loadData();
    const id = setInterval(() => void loadData(), POLL_INTERVAL_MS);
    return () => {
      cancelRef.current++;
      clearInterval(id);
    };
  }, [loadData]);

  return { closures, loading, error };
}
