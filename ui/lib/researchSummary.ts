import { formatAlpha, stageLabel } from "./researchFormat";
import type { ResearchOverview } from "./researchTypes";

/** Short plain-language paragraphs for the top of the Overview tab, built from the data. */
export function plainSummary(data: ResearchOverview): string[] {
  const { status, baseline, ideas } = data;
  const lines: string[] = [];

  if (baseline) {
    const used = baseline.stages.map((s) => `${s.strategy} for ${s.label.split(":")[0].toLowerCase()}`);
    lines.push(`Baseline v${baseline.version} is locked: ${used.join(", ")}. Every new idea has to add money on top of it.`);
  }
  lines.push(
    `We have looked at ${ideas.length} ideas in ${status.looks} counted looks. Because every look is a chance to be fooled by luck, ` +
      `a new idea now needs a z-score above ${status.promotion_bar.toFixed(2)} before we take it seriously.`,
  );
  const nextAlpha = status.next_trial_alpha === null ? "" : `, and trial ${status.next_trial} may use alpha ${formatAlpha(status.next_trial_alpha)}`;
  lines.push(`${status.trials_run} of ${status.trials_budget} one-shot trials are used${nextAlpha}.`);

  const waiting = ideas.filter((i) => i.status === "candidate");
  if (waiting.length) {
    const names = waiting.map((i) => `${i.name} (${stageLabel(i.stage).toLowerCase()})`).join(", ");
    lines.push(`Waiting for a decision: ${names}.`);
  }
  return lines;
}
