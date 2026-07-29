"use client";

import { useState, useEffect, useRef, useCallback } from "react";

import type { MistakePeriodBucket } from "./types";
import type { StatsFiltersParam } from "./api";

import { fetchMistakeTimeseries } from "./api";

const POLL_INTERVAL_MS = 30_000;

type Granularity = "week" | "month";

interface UseMistakeTimeseriesResult {
  data: MistakePeriodBucket[];
  loading: boolean;
}

export function useMistakeTimeseries(
  filters: StatsFiltersParam = {},
  granularity: Granularity = "week",
): UseMistakeTimeseriesResult {
  const [data, setData] = useState<MistakePeriodBucket[]>([]);
  const [loading, setLoading] = useState(true);
  const cancelRef = useRef(0);

  const key = JSON.stringify({ filters, granularity });

  const load = useCallback(async () => {
    const id = ++cancelRef.current;
    try {
      const parsed = JSON.parse(key) as { filters: StatsFiltersParam; granularity: Granularity };
      const result = await fetchMistakeTimeseries(parsed.filters, parsed.granularity);
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
