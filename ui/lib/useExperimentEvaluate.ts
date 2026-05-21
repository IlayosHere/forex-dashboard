"use client";

import { useState, useRef, useCallback } from "react";

import { evaluateExperiment } from "./gatesApi";
import type { ExperimentEvaluateRequest } from "./gatesApi";
import type { ExperimentResult } from "./gatesTypes";

export interface UseExperimentEvaluateResult {
  result: ExperimentResult | null;
  loading: boolean;
  error: string | null;
  evaluate: (body: ExperimentEvaluateRequest) => Promise<ExperimentResult | null>;
  reset: () => void;
}

export function useExperimentEvaluate(): UseExperimentEvaluateResult {
  const [result, setResult] = useState<ExperimentResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);

  const evaluate = useCallback(
    async (body: ExperimentEvaluateRequest): Promise<ExperimentResult | null> => {
      const id = ++cancelRef.current;
      setLoading(true);
      setError(null);
      try {
        const data = await evaluateExperiment(body);
        if (cancelRef.current !== id) return null;
        setResult(data);
        return data;
      } catch (e) {
        if (cancelRef.current !== id) return null;
        setError(e instanceof Error ? e.message : "Unknown error");
        return null;
      } finally {
        if (cancelRef.current === id) setLoading(false);
      }
    },
    []
  );

  const reset = useCallback(() => {
    cancelRef.current++;
    setResult(null);
    setError(null);
    setLoading(false);
  }, []);

  return { result, loading, error, evaluate, reset };
}
