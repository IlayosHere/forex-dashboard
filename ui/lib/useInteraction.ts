"use client";

import { useEffect, useState } from "react";

import type { InteractionResponse } from "@/lib/types";

import { BASE_URL, authFetch } from "@/lib/api";

export interface UseInteractionResult {
  data: InteractionResponse | null;
  loading: boolean;
  error: string | null;
}

export function useInteraction(
  strategy: string,
  paramA: string,
  paramB: string,
  symbol?: string,
): UseInteractionResult {
  const [data, setData] = useState<InteractionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!strategy || !paramA || !paramB) return;

    const controller = new AbortController();
    setLoading(true);
    setError(null);

    const params = new URLSearchParams({ strategy, param_a: paramA, param_b: paramB });
    if (symbol) params.set("symbol", symbol);

    authFetch(`${BASE_URL}/api/analytics/interaction?${params.toString()}`, {
      signal: controller.signal,
      cache: "no-store",
    })
      .then((res) => {
        if (!res.ok) throw new Error(`Interaction fetch failed: ${res.status}`);
        return res.json() as Promise<InteractionResponse>;
      })
      .then((json) => {
        setData(json);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Unknown error");
        setLoading(false);
      });

    return () => controller.abort();
  }, [strategy, paramA, paramB, symbol]);

  return { data, loading, error };
}
