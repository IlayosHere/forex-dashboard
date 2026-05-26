import { authFetch, BASE_URL } from "./api";

import type { GateSet, GateCondition, GatePreviewResponse, GradeThresholds, Experiment, ExperimentResult } from "./gatesTypes";

// ---------------------------------------------------------------------------
// Gate Sets
// ---------------------------------------------------------------------------

export interface GateSetCreateRequest {
  strategy: string;
  name: string;
  description?: string | null;
  conditions: GateCondition[];
}

export interface GateSetUpdateRequest {
  name?: string;
  description?: string | null;
  conditions?: GateCondition[];
}

export interface GatePreviewRequest {
  strategy: string;
  conditions: GateCondition[];
}

export async function fetchGateSets(strategy?: string): Promise<GateSet[]> {
  const params = new URLSearchParams();
  if (strategy) params.set("strategy", strategy);
  const qs = params.toString();
  const res = await authFetch(`${BASE_URL}/api/gate-sets${qs ? `?${qs}` : ""}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch gate sets: ${res.status}`);
  return res.json() as Promise<GateSet[]>;
}

export async function fetchGateSet(id: string): Promise<GateSet> {
  const res = await authFetch(`${BASE_URL}/api/gate-sets/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch gate set ${id}: ${res.status}`);
  return res.json() as Promise<GateSet>;
}

export async function createGateSet(body: GateSetCreateRequest): Promise<GateSet> {
  const res = await authFetch(`${BASE_URL}/api/gate-sets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to create gate set: ${res.status}`);
  return res.json() as Promise<GateSet>;
}

export async function updateGateSet(id: string, body: GateSetUpdateRequest): Promise<GateSet> {
  const res = await authFetch(`${BASE_URL}/api/gate-sets/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to update gate set: ${res.status}`);
  return res.json() as Promise<GateSet>;
}

export async function activateGateSet(id: string): Promise<GateSet> {
  const res = await authFetch(`${BASE_URL}/api/gate-sets/${id}/activate`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to activate gate set: ${res.status}`);
  return res.json() as Promise<GateSet>;
}

export async function deleteGateSet(id: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/gate-sets/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete gate set: ${res.status}`);
}

export async function previewGateSet(body: GatePreviewRequest): Promise<GatePreviewResponse> {
  const res = await authFetch(`${BASE_URL}/api/gate-sets/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to preview gate set: ${res.status}`);
  return res.json() as Promise<GatePreviewResponse>;
}

// ---------------------------------------------------------------------------
// Grade Thresholds
// ---------------------------------------------------------------------------

export async function fetchGradeThresholds(strategy: string): Promise<GradeThresholds> {
  const res = await authFetch(
    `${BASE_URL}/api/grade-thresholds?strategy=${encodeURIComponent(strategy)}`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error(`Failed to fetch grade thresholds: ${res.status}`);
  return res.json() as Promise<GradeThresholds>;
}

export async function updateGradeThresholds(
  strategy: string,
  body: { a_min: number; b_min: number }
): Promise<GradeThresholds> {
  const res = await authFetch(
    `${BASE_URL}/api/grade-thresholds?strategy=${encodeURIComponent(strategy)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }
  );
  if (!res.ok) throw new Error(`Failed to update grade thresholds: ${res.status}`);
  return res.json() as Promise<GradeThresholds>;
}

export async function recomputeGrades(strategy: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/grade-thresholds/recompute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strategy }),
  });
  if (!res.ok) throw new Error(`Failed to recompute grades: ${res.status}`);
}

// ---------------------------------------------------------------------------
// Auto-gate optimizer
// ---------------------------------------------------------------------------

export interface OptimizeRequest {
  strategy: string;
  min_pass_rate?: number;
  dry_run?: boolean;
}

export interface OptimizeResponse {
  strategy: string;
  conditions_selected: { param: string; op: string; value: string }[];
  win_rate_baseline: number | null;
  win_rate_optimized: number | null;
  delta: number | null;
  pass_rate: number | null;
  pass_count: number;
  total_signals: number;
  confirmed_params_found: number;
  dry_run: boolean;
  gate_set_id: string | null;
  reason: string | null;
}

export async function runAutoOptimize(body: OptimizeRequest): Promise<OptimizeResponse> {
  const res = await authFetch(`${BASE_URL}/api/auto-gate/optimize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Auto-optimize failed: ${res.status}`);
  return res.json() as Promise<OptimizeResponse>;
}

export async function runAutoRecomputeGrades(strategy: string): Promise<{ strategy: string; recomputed: number }> {
  const res = await authFetch(`${BASE_URL}/api/auto-gate/recompute-grades`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ strategy }),
  });
  if (!res.ok) throw new Error(`Grade recompute failed: ${res.status}`);
  return res.json() as Promise<{ strategy: string; recomputed: number }>;
}

// ---------------------------------------------------------------------------
// Experiments
// ---------------------------------------------------------------------------

export interface ExperimentCreateRequest {
  name: string;
  strategy: string;
  conditions: GateCondition[];
  date_from?: string | null;
  date_to?: string | null;
  notes?: string | null;
}

export interface ExperimentUpdateRequest {
  name?: string;
  conditions?: GateCondition[];
  date_from?: string | null;
  date_to?: string | null;
  notes?: string | null;
}

export interface ExperimentEvaluateRequest {
  strategy: string;
  conditions: GateCondition[];
  date_from?: string | null;
  date_to?: string | null;
}

export async function fetchExperiments(strategy?: string): Promise<Experiment[]> {
  const params = new URLSearchParams();
  if (strategy) params.set("strategy", strategy);
  const qs = params.toString();
  const res = await authFetch(`${BASE_URL}/api/experiments${qs ? `?${qs}` : ""}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch experiments: ${res.status}`);
  return res.json() as Promise<Experiment[]>;
}

export async function fetchExperiment(id: string): Promise<Experiment> {
  const res = await authFetch(`${BASE_URL}/api/experiments/${id}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Failed to fetch experiment ${id}: ${res.status}`);
  return res.json() as Promise<Experiment>;
}

export async function createExperiment(body: ExperimentCreateRequest): Promise<Experiment> {
  const res = await authFetch(`${BASE_URL}/api/experiments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to create experiment: ${res.status}`);
  return res.json() as Promise<Experiment>;
}

export async function updateExperiment(id: string, body: ExperimentUpdateRequest): Promise<Experiment> {
  const res = await authFetch(`${BASE_URL}/api/experiments/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to update experiment: ${res.status}`);
  return res.json() as Promise<Experiment>;
}

export async function deleteExperiment(id: string): Promise<void> {
  const res = await authFetch(`${BASE_URL}/api/experiments/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete experiment: ${res.status}`);
}

export async function evaluateExperiment(body: ExperimentEvaluateRequest): Promise<ExperimentResult> {
  const res = await authFetch(`${BASE_URL}/api/experiments/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to evaluate experiment: ${res.status}`);
  return res.json() as Promise<ExperimentResult>;
}

export async function runExperiment(id: string): Promise<ExperimentResult> {
  const res = await authFetch(`${BASE_URL}/api/experiments/${id}/run`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to run experiment: ${res.status}`);
  return res.json() as Promise<ExperimentResult>;
}
