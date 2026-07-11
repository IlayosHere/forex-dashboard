"use client";

import { useState, useEffect, useRef, useCallback } from "react";

import type { MistakeStat } from "./types";
import type { StatsFiltersParam } from "./api";

import { fetchMistakeStats } from "./api";

const POLL_INTERVAL_MS = 30_000;

interface UseMistakeStatsResult {
  data: MistakeStat[];
  loading: boolean;
}

export function useMistakeStats(filters: StatsFiltersParam = {}): UseMistakeStatsResult {
  const [data, setData] = useState<MistakeStat[]>([]);
  const [loading, setLoading] = useState(true);
  const cancelRef = useRef(0);

  const key = JSON.stringify(filters);

  const load = useCallback(async () => {
    const id = ++cancelRef.current;
    try {
      const result = await fetchMistakeStats(JSON.parse(key) as typeof filters);
      if (cancelRef.current !== id) return;
      setData(result);
    } catch {
      // silently fail — panel stays with previous data
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

  return { data, loading };
}
