"use client";

import { useCallback, useEffect, useState } from "react";

import { fetchResearch } from "./researchApi";
import type { ResearchOverview } from "./researchTypes";

interface UseResearchResult {
  data: ResearchOverview | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useResearch(): UseResearchResult {
  const [data, setData] = useState<ResearchOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setData(await fetchResearch());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, loading, error, refetch: load };
}
