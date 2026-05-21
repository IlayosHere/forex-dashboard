"use client";

import { useState, useEffect, useRef, useCallback } from "react";

import { previewGateSet } from "./gatesApi";
import type { GateCondition, GatePreviewResponse } from "./gatesTypes";

const DEBOUNCE_MS = 500;

export interface UseGatePreviewResult {
  preview: GatePreviewResponse | null;
  loading: boolean;
  error: string | null;
}

export function useGatePreview(
  strategy: string,
  conditions: GateCondition[]
): UseGatePreviewResult {
  const [preview, setPreview] = useState<GatePreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const cancelRef = useRef(0);

  const conditionsKey = JSON.stringify(conditions);

  const run = useCallback(
    async (parsedConditions: GateCondition[], requestId: number) => {
      if (parsedConditions.length === 0) {
        setPreview(null);
        setLoading(false);
        return;
      }
      try {
        const data = await previewGateSet({ strategy, conditions: parsedConditions });
        if (cancelRef.current !== requestId) return;
        setPreview(data);
        setError(null);
      } catch (e) {
        if (cancelRef.current !== requestId) return;
        setError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        if (cancelRef.current === requestId) setLoading(false);
      }
    },
    [strategy]
  );

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    const parsed = JSON.parse(conditionsKey) as GateCondition[];
    if (parsed.length === 0) {
      setPreview(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    const id = ++cancelRef.current;
    timerRef.current = setTimeout(() => { void run(parsed, id); }, DEBOUNCE_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [conditionsKey, run]);

  return { preview, loading, error };
}
