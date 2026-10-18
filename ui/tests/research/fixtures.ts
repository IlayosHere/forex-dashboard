import type { ResearchIdea, ResearchOverview } from "@/lib/researchTypes";

export function makeIdea(over: Partial<ResearchIdea> = {}): ResearchIdea {
  return {
    id: "ALPHA", name: "Alpha idea", stage: "3", status: "killed", round: null,
    rule: "Do a thing", plain: "Nothing there.", notes: null, years: null,
    report: "results/exploration/agents/x.md", log: [1], trials: [], results: [],
    ...over,
  };
}

export function makeOverview(over: Partial<ResearchOverview> = {}): ResearchOverview {
  return {
    status: {
      looks: 110, promotion_bar: 3.07, log_entries: 11, trials_run: 7, trials_budget: 10, trials_left: 3,
      next_trial: 8, next_trial_alpha: 0.015, alpha_project_total: 0.05, pipeline_value: "Pays $428 per eval.",
    },
    baseline: {
      version: 1, adopted_on: "2026-10-17", mechanism: "One mechanism.",
      stages: [
        { key: "stage_1_eval", label: "Stage 1: Eval", strategy: "BETA", rule: "Beta rule", fires_on: "24% of days",
          edges: [{ period: "fresh 2010-2017", value: "+6.7" }], planning_value: "+5" },
        { key: "stage_3_green_days", label: "Stage 3: Green days", strategy: "GAMMA", rule: "Gamma rule", fires_on: null,
          edges: [], planning_value: null },
      ],
      funded_rules: [{ label: "Payout policy", text: "Max as soon as eligible" }],
      challenger_rules: [{ label: "Principle", text: "Add value on top." }],
    },
    ideas: [
      makeIdea({ id: "BETA", name: "Beta", status: "confirmed", stage: "1,2", plain: "Works.",
        results: [{ label: "Trial", market: "NQ", n: 444, hit: 60.7, control: 54.1, excess: 6.7, z: 2.94 }] }),
      makeIdea({ id: "CAND", name: "Candidate idea", status: "candidate", plain: "Promising.",
        results: [{ label: "NQ", market: "NQ", n: 643, hit: null, control: null, excess: 5.5, z: 3.49 }] }),
      makeIdea({ id: "ALPHA", name: "Alpha idea", status: "killed" }),
      makeIdea({ id: "PARK", name: "Parked idea", status: "parked", stage: "1" }),
    ],
    trials: [],
    alpha_plan: [{ trial: 8, alpha: 0.015, state: "open" }],
    exploration_log: [], lessons: ["Count every look."],
    journey: [{ date: "2026-10-17", kind: "decision", title: "Lock the baseline", detail: "It passed." }],
    queue: [], warnings: [], source: "local:test", fetched_at: "2026-10-17 12:00 UTC",
    ...over,
  };
}
