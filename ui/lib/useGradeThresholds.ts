"use client";

import { useState, useEffect, useCallback, useRef } from "react";

import { fetchGradeThresholds, updateGradeThresholds, recomputeGrades } from "./gatesApi";
import type { GradeThresholds } from "./gatesTypes";

export interface UseGradeThresholdsResult {
  thresholds: GradeThresholds | null;
  loading: boolean;
  error: string | null;
  update: (aMin: number, bMin: number) => Promise<void>;
  recompute: () => Promise<void>;
  refetch: () => void;
}

export function useGradeThresholds(strategy: string): UseGradeThresholdsResult {
  const [thresholds, setThresholds] = useState<GradeThresholds | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);

  const load = useCallback(async () => {
    const id = ++cancelRef.current;
    try {
      const data = await fetchGradeThresholds(strategy);
      if (cancelRef.current !== id) return;
      setThresholds(data);
      setError(null);
    } catch (e) {
      if (cancelRef.current !== id) return;
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      if (cancelRef.current === id) setLoading(false);
    }
  }, [strategy]);

  useEffect(() => {
    setLoading(true);
    void load();
    return () => { cancelRef.current++; };
  }, [load]);

  const update = useCallback(async (aMin: number, bMin: number): Promise<void> => {
    const data = await updateGradeThresholds(strategy, { a_min: aMin, b_min: bMin });
    setThresholds(data);
  }, [strategy]);

  const recompute = useCallback(async (): Promise<void> => {
    await recomputeGrades(strategy);
    await load();
  }, [strategy, load]);

  return { thresholds, loading, error, update, recompute, refetch: load };
}
