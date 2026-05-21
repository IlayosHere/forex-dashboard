"use client";

import { useState, useEffect, useCallback, useRef } from "react";

import { fetchExperiments, createExperiment, updateExperiment, deleteExperiment } from "./gatesApi";
import type { ExperimentCreateRequest, ExperimentUpdateRequest } from "./gatesApi";
import type { Experiment } from "./gatesTypes";

export interface UseExperimentsResult {
  experiments: Experiment[];
  loading: boolean;
  error: string | null;
  create: (body: ExperimentCreateRequest) => Promise<Experiment>;
  update: (id: string, body: ExperimentUpdateRequest) => Promise<Experiment>;
  remove: (id: string) => Promise<void>;
  refetch: () => void;
}

export function useExperiments(strategy?: string): UseExperimentsResult {
  const [experiments, setExperiments] = useState<Experiment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);
  const strategyKey = strategy ?? "";

  const load = useCallback(async () => {
    const id = ++cancelRef.current;
    try {
      const data = await fetchExperiments(strategyKey || undefined);
      if (cancelRef.current !== id) return;
      setExperiments(data);
      setError(null);
    } catch (e) {
      if (cancelRef.current !== id) return;
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      if (cancelRef.current === id) setLoading(false);
    }
  }, [strategyKey]);

  useEffect(() => {
    setLoading(true);
    void load();
    return () => { cancelRef.current++; };
  }, [load]);

  const create = useCallback(async (body: ExperimentCreateRequest): Promise<Experiment> => {
    const exp = await createExperiment(body);
    setExperiments((prev) => [...prev, exp]);
    return exp;
  }, []);

  const update = useCallback(async (id: string, body: ExperimentUpdateRequest): Promise<Experiment> => {
    const exp = await updateExperiment(id, body);
    setExperiments((prev) => prev.map((e) => (e.id === id ? exp : e)));
    return exp;
  }, []);

  const remove = useCallback(async (id: string): Promise<void> => {
    await deleteExperiment(id);
    setExperiments((prev) => prev.filter((e) => e.id !== id));
  }, []);

  return { experiments, loading, error, create, update, remove, refetch: load };
}
