"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { fetchLifeEntry } from "./api";
import type { LifeEntry } from "./types";

interface UseLifeEntryResult {
  entry: LifeEntry | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useLifeEntry(id: string): UseLifeEntryResult {
  const [entry, setEntry] = useState<LifeEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);

  const load = useCallback(async () => {
    const seq = ++cancelRef.current;
    try {
      const data = await fetchLifeEntry(id);
      if (cancelRef.current !== seq) return;
      setEntry(data);
      setError(null);
    } catch (e) {
      if (cancelRef.current !== seq) return;
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      if (cancelRef.current === seq) setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    setLoading(true);
    void load();
    return () => { cancelRef.current++; };
  }, [load]);

  return { entry, loading, error, refetch: load };
}
