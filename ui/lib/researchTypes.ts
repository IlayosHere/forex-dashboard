export type IdeaStatus = "confirmed" | "candidate" | "parked" | "killed";
export type QueueKind = "idea" | "note";
export type QueueStage = "1" | "2" | "3" | "any";
export type QueueStatus = "queued" | "picked_up" | "answered";

export interface ResearchStatus {
  looks: number;
  promotion_bar: number;
  log_entries: number;
  trials_run: number;
  trials_budget: number;
  trials_left: number;
  next_trial: number;
  next_trial_alpha: number | null;
  alpha_project_total: number | null;
  pipeline_value: string | null;
}

export interface ResearchNote {
  label: string;
  text: string;
}

export interface ResearchEdge {
  period: string;
  value: string;
}

export interface StageCardData {
  key: string;
  label: string;
  strategy: string;
  rule: string;
  fires_on: string | null;
  edges: ResearchEdge[];
  planning_value: string | null;
}

export interface Baseline {
  version: number;
  adopted_on: string;
  mechanism: string;
  stages: StageCardData[];
  funded_rules: ResearchNote[];
  challenger_rules: ResearchNote[];
}

export interface IdeaResult {
  label: string;
  market: string | null;
  n: number | null;
  hit: number | null;
  control: number | null;
  excess: number | null;
  z: number | null;
}

export interface ResearchIdea {
  id: string;
  name: string;
  stage: string;
  status: IdeaStatus;
  round: string | null;
  rule: string;
  plain: string;
  notes: string | null;
  years: string | null;
  report: string;
  log: number[];
  trials: number[];
  results: IdeaResult[];
}

export interface ResearchTrial {
  trial_no: number;
  hypothesis_id: string;
  period: string;
  when: string;
  n_trades: number | null;
  hit_rate: number | null;
  control_hit_rate: number | null;
  z_vs_control: number | null;
  z_decision: number | null;
  excess_pts: number | null;
  verdict: string;
  alpha: number | null;
  notes: string;
}

export interface AlphaRow {
  trial: number;
  alpha: number;
  state: "passed" | "failed" | "open";
}

export interface LogEntry {
  n: number;
  date: string;
  idea: string;
  looked_at: string;
  variants: number;
  result: string;
}

export interface JourneyItem {
  date: string;
  kind: "decision" | "trial" | "exploration";
  title: string;
  detail: string;
}

export interface QueueItem {
  id: string;
  kind: QueueKind;
  title: string;
  stage: string;
  about: string | null;
  status: QueueStatus;
  submitted_at: string;
  submitted_by: string | null;
  round: string | null;
  answer: string | null;
  body: string;
}

export interface QueueCreate {
  kind: QueueKind;
  title: string;
  stage: QueueStage;
  about: string | null;
  body: string;
}

export interface ResearchOverview {
  status: ResearchStatus;
  baseline: Baseline | null;
  ideas: ResearchIdea[];
  trials: ResearchTrial[];
  alpha_plan: AlphaRow[];
  exploration_log: LogEntry[];
  lessons: string[];
  journey: JourneyItem[];
  queue: QueueItem[];
  warnings: string[];
  source: string;
  fetched_at: string;
}
