"use client";

import { useCallback, useEffect, useState } from "react";

import type {
  CheckpointCreateRequest,
  PlanUpsertRequest,
  PremarketPlan,
  ReviewUpsertRequest,
  ScenarioCreateRequest,
  ScenarioUpdateRequest,
} from "./types";

import {
  addPlanCheckpoint,
  createPlanScenario,
  deletePlanScenario,
  fetchPremarketPlan,
  updatePlanScenario,
  upsertPlanReview,
  upsertPremarketPlan,
} from "./api";

export interface UsePremarketPlanResult {
  plan: PremarketPlan | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  savePlan: (data: PlanUpsertRequest) => Promise<void>;
  addScenario: (data: ScenarioCreateRequest) => Promise<void>;
  updateScenario: (scenarioId: string, data: ScenarioUpdateRequest) => Promise<void>;
  removeScenario: (scenarioId: string) => Promise<void>;
  addCheckpoint: (data: CheckpointCreateRequest) => Promise<void>;
  saveReview: (data: ReviewUpsertRequest) => Promise<void>;
  refetch: () => void;
}

export function usePremarketPlan(date: string | null): UsePremarketPlanResult {
  const [plan, setPlan] = useState<PremarketPlan | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    if (!date) return;
    setLoading(true);
    setError(null);
    fetchPremarketPlan(date)
      .then(setPlan)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load plan"))
      .finally(() => setLoading(false));
  }, [date, tick]);

  const savePlan = useCallback(async (data: PlanUpsertRequest): Promise<void> => {
    if (!date) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await upsertPremarketPlan(date, data);
      setPlan(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save plan");
      throw err;
    } finally {
      setSaving(false);
    }
  }, [date]);

  const addScenario = useCallback(async (data: ScenarioCreateRequest): Promise<void> => {
    if (!date) return;
    setSaving(true);
    setError(null);
    try {
      await createPlanScenario(date, data);
      const updated = await fetchPremarketPlan(date);
      setPlan(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add scenario");
      throw err;
    } finally {
      setSaving(false);
    }
  }, [date]);

  const updateScenario = useCallback(async (scenarioId: string, data: ScenarioUpdateRequest): Promise<void> => {
    if (!date) return;
    setSaving(true);
    setError(null);
    try {
      await updatePlanScenario(scenarioId, data);
      const updated = await fetchPremarketPlan(date);
      setPlan(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update scenario");
      throw err;
    } finally {
      setSaving(false);
    }
  }, [date]);

  const removeScenario = useCallback(async (scenarioId: string): Promise<void> => {
    if (!date) return;
    setSaving(true);
    setError(null);
    try {
      await deletePlanScenario(scenarioId);
      const updated = await fetchPremarketPlan(date);
      setPlan(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to delete scenario");
      throw err;
    } finally {
      setSaving(false);
    }
  }, [date]);

  const addCheckpoint = useCallback(async (data: CheckpointCreateRequest): Promise<void> => {
    if (!date) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await addPlanCheckpoint(date, data);
      setPlan(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to add checkpoint");
      throw err;
    } finally {
      setSaving(false);
    }
  }, [date]);

  const saveReview = useCallback(async (data: ReviewUpsertRequest): Promise<void> => {
    if (!date) return;
    setSaving(true);
    setError(null);
    try {
      await upsertPlanReview(date, data);
      const updated = await fetchPremarketPlan(date);
      setPlan(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save review");
      throw err;
    } finally {
      setSaving(false);
    }
  }, [date]);

  const refetch = useCallback(() => setTick((t) => t + 1), []);

  return {
    plan, loading, saving, error,
    savePlan, addScenario, updateScenario, removeScenario, addCheckpoint, saveReview,
    refetch,
  };
}
