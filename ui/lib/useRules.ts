"use client";

import { useState, useEffect, useCallback } from "react";

import type { Rule } from "./types";

import { fetchRules } from "./api";

interface UseRulesResult {
  rules: Rule[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useRules(): UseRulesResult {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchRules();
      setRules(data);
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

  return { rules, loading, error, refetch: load };
}
