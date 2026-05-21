export type GateStatus = "passed" | "blocked" | "no_gates" | "error";
export type SignalGrade = "A" | "B" | "C" | "D";

export type ConditionOperator =
  | "eq" | "ne" | "in" | "not_in"
  | "gte" | "lte" | "between"
  | "is_null" | "not_null";

export interface GateCondition {
  param: string;
  op: ConditionOperator;
  value?: unknown;
  values?: unknown[];
  low?: number;
  high?: number;
}

export interface GateSet {
  id: string;
  strategy: string;
  name: string;
  description: string | null;
  is_active: boolean;
  conditions: GateCondition[];
  created_at: string;
  updated_at: string;
}

export interface GatePreviewResponse {
  total_signals_evaluated: number;
  pass_count: number;
  block_count: number;
  pass_rate: number;
  win_rate_passed: number | null;
  win_rate_baseline: number | null;
  delta_vs_baseline: number | null;
  per_condition_failure_count: number[];
}

export interface GradeThresholds {
  id: string;
  strategy: string;
  a_min: number;
  b_min: number;
  is_active: boolean;
  created_at: string;
}

export interface BucketStat {
  bucket: string;
  n: number;
  wins: number;
  win_rate: number;
  ci_lo: number;
  ci_hi: number;
}

export interface ParamBreakdown {
  param_name: string;
  buckets: BucketStat[];
}

export interface ExperimentResult {
  strategy: string;
  date_from: string | null;
  date_to: string | null;
  total_signals: number;
  resolved_signals: number;
  passing_signals: number;
  resolved_passing: number;
  win_rate_passed: number | null;
  win_rate_baseline: number;
  delta_vs_baseline: number | null;
  per_condition_failure_count: number[];
  per_param_breakdown: ParamBreakdown[];
}

export interface Experiment {
  id: string;
  name: string;
  strategy: string;
  conditions: GateCondition[];
  date_from: string | null;
  date_to: string | null;
  notes: string | null;
  last_run_at: string | null;
  last_summary: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}
