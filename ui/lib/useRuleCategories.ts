"use client";

import { useState, useEffect, useCallback } from "react";

import type { RuleCategory } from "./types";

import { fetchRuleCategories } from "./api";

interface UseRuleCategoriesResult {
  categories: RuleCategory[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useRuleCategories(): UseRuleCategoriesResult {
  const [categories, setCategories] = useState<RuleCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchRuleCategories();
      setCategories(data);
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

  return { categories, loading, error, refetch: load };
}
