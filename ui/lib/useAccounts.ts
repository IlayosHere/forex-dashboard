"use client";

import { useState, useEffect, useCallback } from "react";
import { fetchAccounts } from "./api";
import type { Account } from "./types";

interface UseAccountsResult {
  accounts: Account[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useAccounts(): UseAccountsResult {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchAccounts();
      setAccounts(data);
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

  return { accounts, loading, error, refetch: load };
}
