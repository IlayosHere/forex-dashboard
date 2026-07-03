"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { fetchLifeEntries, type LifeEntryFilters } from "./api";
import type { LifeEntry } from "./types";

interface UseLifeEntriesResult {
  entries: LifeEntry[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useLifeEntries(filters: LifeEntryFilters = {}): UseLifeEntriesResult {
  const [entries, setEntries] = useState<LifeEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);

  const key = JSON.stringify(filters);

  const load = useCallback(async () => {
    const id = ++cancelRef.current;
    const parsed = JSON.parse(key) as LifeEntryFilters;
    try {
      const data = await fetchLifeEntries(parsed);
      if (cancelRef.current !== id) return;
      setEntries(data);
      setError(null);
    } catch (e) {
      if (cancelRef.current !== id) return;
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      if (cancelRef.current === id) setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  useEffect(() => {
    if (entries.length === 0) setLoading(true);
    void load();
    return () => { cancelRef.current++; };
  }, [load]);

  return { entries, loading, error, refetch: load };
}
