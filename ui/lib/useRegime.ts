"use client";

import { useState, useEffect } from "react";

import { BASE_URL, authFetch } from "./api";

import type { RegimeResult } from "./types";

export interface UseRegimeResult {
  data: RegimeResult | null;
  loading: boolean;
  error: string | null;
}

export function useRegime(strategy: string, symbol?: string): UseRegimeResult {
  const [data, setData] = useState<RegimeResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function load(): Promise<void> {
      setLoading(true);
      try {
        const params = new URLSearchParams({ strategy });
        if (symbol) params.set("symbol", symbol);
        const res = await authFetch(`${BASE_URL}/api/analytics/regime?${params}`, {
          signal: controller.signal,
        });
        if (!res.ok) {
          throw new Error(`Request failed: ${res.status}`);
        }
        const json = (await res.json()) as RegimeResult;
        setData(json);
        setError(null);
      } catch (e) {
        if ((e as { name?: string }).name === "AbortError") return;
        setError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    }

    void load();
    return () => controller.abort();
  }, [strategy, symbol]);

  return { data, loading, error };
}
