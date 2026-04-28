"use client";

import { useEffect, useState } from "react";

import type { TopCombinationsResponse } from "@/lib/types";

import { BASE_URL, authFetch } from "@/lib/api";

export interface UseTopCombinationsResult {
  data: TopCombinationsResponse | null;
  loading: boolean;
  error: string | null;
}

export function useTopCombinations(
  strategy: string,
  symbol?: string,
): UseTopCombinationsResult {
  const [data, setData] = useState<TopCombinationsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!strategy) return;

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({ strategy });
    if (symbol) params.set("symbol", symbol);

    authFetch(`${BASE_URL}/api/analytics/top-combinations?${params.toString()}`, {
      signal: controller.signal,
      cache: "no-store",
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Top combinations fetch failed: ${res.status}`);
        return res.json() as Promise<TopCombinationsResponse>;
      })
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") {
          setLoading(false);
          return;
        }
        setError(err instanceof Error ? err.message : "Unknown error");
        setLoading(false);
      });

    return () => controller.abort();
  }, [strategy, symbol]);

  return { data, loading, error };
}
