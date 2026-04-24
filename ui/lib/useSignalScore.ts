"use client";

import { useState, useCallback, useRef } from "react";

import { authFetch, BASE_URL } from "@/lib/api";

import type { ScoreResponse } from "@/lib/types";

export interface UseSignalScoreResult {
  data: ScoreResponse | null;
  loading: boolean;
  fetch: () => void;
}

export function useSignalScore(
  signalId: string,
  strategy: string,
): UseSignalScoreResult {
  const [data, setData] = useState<ScoreResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const loadingRef = useRef(false);

  const fetchScore = useCallback(() => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setLoading(true);
    const params = new URLSearchParams({ strategy });
    authFetch(`${BASE_URL}/api/analytics/score/${signalId}?${params}`)
      .then((res) => {
        if (!res.ok) return null;
        return res.json() as Promise<ScoreResponse>;
      })
      .then((json) => {
        setData(json);
      })
      .catch(() => {
        setData(null);
      })
      .finally(() => {
        loadingRef.current = false;
        setLoading(false);
      });
  }, [signalId, strategy]);

  return { data, loading, fetch: fetchScore };
}
