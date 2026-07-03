"use client";

import { useEffect, useState } from "react";

import type { PremarketDaySummary } from "./types";

import { fetchPremarketMonth } from "./api";

export interface UsePremarketMonthResult {
  data: PremarketDaySummary[];
  loading: boolean;
}

export function usePremarketMonth(from: string, to: string): UsePremarketMonthResult {
  const [data, setData] = useState<PremarketDaySummary[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchPremarketMonth(from, to)
      .then(setData)
      .catch(() => setData([]))
      .finally(() => setLoading(false));
  }, [from, to]);

  return { data, loading };
}
