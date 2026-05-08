"use client";

import { useCallback, useEffect, useState } from "react";

import type { SessionUpsertRequest, TradingSession } from "./types";

import { fetchSession, upsertSession } from "./api";

export interface UseSessionResult {
  session: TradingSession | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  save: (data: SessionUpsertRequest) => Promise<void>;
  refetch: () => void;
}

export function useSession(date: string | null): UseSessionResult {
  const [session, setSession] = useState<TradingSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!date) return;
    setLoading(true);
    setError(null);
    fetchSession(date)
      .then(setSession)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load session"))
      .finally(() => setLoading(false));
  }, [date, tick]);

  const save = useCallback(async (data: SessionUpsertRequest): Promise<void> => {
    if (!date) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await upsertSession(date, data);
      setSession(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save session");
      throw err;
    } finally {
      setSaving(false);
    }
  }, [date]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  return { session, loading, saving, error, save, refetch };
}
