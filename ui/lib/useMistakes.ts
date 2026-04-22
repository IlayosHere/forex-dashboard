"use client";

import { useState, useEffect, useCallback } from "react";

import type { Mistake } from "./types";

import { fetchMistakes } from "./api";

interface UseMistakesResult {
  mistakes: Mistake[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useMistakes(): UseMistakesResult {
  const [mistakes, setMistakes] = useState<Mistake[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchMistakes();
      setMistakes(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    void load();
  }, [load]);

  return { mistakes, loading, error, refetch: load };
}
