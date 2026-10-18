import { formatAlpha, headline, stageLabel } from "@/lib/researchFormat";
import { plainSummary } from "@/lib/researchSummary";
import type { ResearchOverview } from "@/lib/researchTypes";

import { Glossary } from "./Glossary";
import { JourneyRow } from "./JourneyRow";
import type { ResearchTab } from "./ResearchTabs";
import { Section } from "./Section";
import { StatTile } from "./StatTile";

interface OverviewTabProps {
  data: ResearchOverview;
  onNavigate: (tab: ResearchTab) => void;
}

export function OverviewTab({ data, onNavigate }: OverviewTabProps) {
  const { status } = data;
  const waiting = data.ideas.filter((i) => i.status === "candidate");
  const alphaText = status.next_trial_alpha === null ? "n/a" : formatAlpha(status.next_trial_alpha);
  const total = status.alpha_project_total === null ? "" : ` The whole project shares ${formatAlpha(status.alpha_project_total)}.`;

  return (
    <div>
      <Section title="In plain words">
        <div className="space-y-2 rounded-lg border border-border bg-surface-raised p-4 text-sm leading-relaxed text-text-primary">
          {plainSummary(data).map((line) => (
            <p key={line}>{line}</p>
          ))}
        </div>
      </Section>

      <div className="mb-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile label="Looks" value={String(status.looks)} caption="Every table of results we have studied, kept or not. More looks means more chances to be fooled by luck." />
        <StatTile label="Promotion bar" value={`z ${status.promotion_bar.toFixed(2)}`} caption="A new idea must score above this to be taken seriously. The bar rises with every look." />
        <StatTile label="Trials left" value={`${status.trials_left} of ${status.trials_budget}`} caption="One-shot tests on data the rule was not built on. Each can be run only once." />
        <StatTile label={`Alpha for trial ${status.next_trial}`} value={alphaText} caption={`The chance of a false pass we allow for the next trial. Smaller is stricter.${total}`} />
      </div>

      {status.pipeline_value && (
        <Section title="What the baseline is worth" hint="From the Lucid simulator, using the confirmed strategies.">
          <p className="max-w-3xl text-sm leading-relaxed text-text-primary">{status.pipeline_value}</p>
        </Section>
      )}

      {waiting.length > 0 && (
        <Section title="Waiting for a decision" hint="Promising ideas that have not been tested for real yet.">
          <div className="space-y-2">
            {waiting.map((idea) => (
              <button
                key={idea.id}
                type="button"
                onClick={() => onNavigate("ideas")}
                className="block w-full rounded-lg border border-accent-gold/30 bg-surface-raised p-4 text-left hover:border-accent-gold/60"
              >
                <div className="text-sm font-medium text-text-primary">
                  {idea.name} <span className="text-xs text-text-muted">({stageLabel(idea.stage)})</span>
                </div>
                <p className="mt-1 text-xs leading-relaxed text-text-muted">{idea.plain}</p>
                {headline(idea) && <p className="mt-2 text-xs tabular-nums text-text-primary">{headline(idea)}</p>}
              </button>
            ))}
          </div>
        </Section>
      )}

      <Section title="What happened lately">
        <div className="rounded-lg border border-border bg-surface-raised px-4">
          {data.journey.slice(0, 6).map((item) => (
            <JourneyRow key={`${item.kind}-${item.date}-${item.title}`} item={item} />
          ))}
        </div>
        <button type="button" onClick={() => onNavigate("journey")} className="mt-2 text-xs text-breakeven hover:underline">
          See the whole journey
        </button>
      </Section>

      {data.lessons.length > 0 && (
        <Section title="Lessons we learned the hard way" hint="These apply to every new idea.">
          <ul className="max-w-3xl list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-text-primary">
            {data.lessons.map((lesson) => (
              <li key={lesson}>{lesson}</li>
            ))}
          </ul>
        </Section>
      )}

      <Glossary />
    </div>
  );
}
