import type { IdeaResult, IdeaStatus, ResearchIdea, ResearchTrial } from "./researchTypes";

export const STATUS_ORDER: IdeaStatus[] = ["confirmed", "candidate", "parked", "killed"];

const STATUS_LABEL: Record<IdeaStatus, string> = {
  confirmed: "Confirmed",
  candidate: "Candidate",
  parked: "Parked",
  killed: "Killed",
};

const STATUS_MEANING: Record<IdeaStatus, string> = {
  confirmed: "Passed its one-shot test on data it had never seen. In use.",
  candidate: "Promising, but not yet tested for real. Waiting for a decision.",
  parked: "Some sign of life, not enough evidence. Kept for later.",
  killed: "Did not work. Not tested again unless the rule is clearly different.",
};

export function statusLabel(status: IdeaStatus): string {
  return STATUS_LABEL[status];
}

export function statusMeaning(status: IdeaStatus): string {
  return STATUS_MEANING[status];
}

export function stageLabel(stage: string): string {
  if (stage === "1,2") return "Stages 1-2";
  if (stage === "any") return "Any stage";
  return `Stage ${stage}`;
}

export function signed(value: number, digits = 1): string {
  const text = value.toFixed(digits);
  return value > 0 ? `+${text}` : text;
}

export function formatAlpha(alpha: number): string {
  return String(Number(alpha.toFixed(4)));
}

/** The result to headline: NQ (the market we trade) first, then the last one with a z-score. */
export function bestResult(idea: ResearchIdea): IdeaResult | null {
  const nq = idea.results.filter((r) => r.market === "NQ");
  const pool = nq.length > 0 ? nq : idea.results;
  const withZ = pool.filter((r) => r.z !== null);
  return withZ.at(-1) ?? pool.at(-1) ?? null;
}

/** One line of numbers for an idea card, or null when none were recorded. */
export function headline(idea: ResearchIdea): string | null {
  const r = bestResult(idea);
  if (!r) return null;
  const parts: string[] = [];
  if (r.excess !== null) parts.push(`${signed(r.excess)} points over random entries`);
  if (r.z !== null) parts.push(`z ${r.z.toFixed(2)}`);
  if (r.n !== null) parts.push(`${r.n.toLocaleString("en-US")} trades`);
  return parts.length ? parts.join(", ") : null;
}

export function countByStatus(ideas: ResearchIdea[]): Record<IdeaStatus, number> {
  const counts: Record<IdeaStatus, number> = { confirmed: 0, candidate: 0, parked: 0, killed: 0 };
  for (const idea of ideas) counts[idea.status] += 1;
  return counts;
}

const PERIOD_LABEL: Record<string, string> = {
  in_sample: "In-sample 2018-2022",
  out_of_sample: "Out of sample 2023-2026",
  fresh_2010_2017: "Fresh data 2010-2017",
  confirm_2018_2026: "Confirmation 2018-2026",
};

export function periodLabel(period: string): string {
  return PERIOD_LABEL[period] ?? period.replace(/_/g, " ");
}

export function verdictLabel(trial: ResearchTrial): string {
  return trial.verdict === "PASS" ? "Passed" : trial.verdict === "FAIL" ? "Failed" : trial.verdict;
}

export function matchesSearch(idea: ResearchIdea, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return [idea.id, idea.name, idea.rule, idea.plain].some((t) => t.toLowerCase().includes(q));
}
