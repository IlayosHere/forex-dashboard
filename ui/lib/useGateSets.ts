"use client";

import { useState, useEffect, useCallback, useRef } from "react";

import { fetchGateSets, createGateSet, updateGateSet, activateGateSet, deleteGateSet } from "./gatesApi";
import type { GateSetCreateRequest, GateSetUpdateRequest } from "./gatesApi";
import type { GateSet } from "./gatesTypes";

export interface UseGateSetsResult {
  gateSets: GateSet[];
  loading: boolean;
  error: string | null;
  create: (body: GateSetCreateRequest) => Promise<GateSet>;
  update: (id: string, body: GateSetUpdateRequest) => Promise<GateSet>;
  activate: (id: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  refetch: () => void;
}

export function useGateSets(strategy?: string): UseGateSetsResult {
  const [gateSets, setGateSets] = useState<GateSet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);
  const strategyKey = strategy ?? "";

  const load = useCallback(async () => {
    const id = ++cancelRef.current;
    try {
      const data = await fetchGateSets(strategyKey || undefined);
      if (cancelRef.current !== id) return;
      setGateSets(data);
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

  const create = useCallback(async (body: GateSetCreateRequest): Promise<GateSet> => {
    const gs = await createGateSet(body);
    setGateSets((prev) => [...prev, gs]);
    return gs;
  }, []);

  const update = useCallback(async (id: string, body: GateSetUpdateRequest): Promise<GateSet> => {
    const gs = await updateGateSet(id, body);
    setGateSets((prev) => prev.map((g) => (g.id === id ? gs : g)));
    return gs;
  }, []);

  const activate = useCallback(async (id: string): Promise<void> => {
    const gs = await activateGateSet(id);
    setGateSets((prev) => prev.map((g) => ({ ...g, is_active: g.id === gs.id })));
  }, []);

  const remove = useCallback(async (id: string): Promise<void> => {
    await deleteGateSet(id);
    setGateSets((prev) => prev.filter((g) => g.id !== id));
  }, []);

  return { gateSets, loading, error, create, update, activate, remove, refetch: load };
}
