import type { ResearchOverview } from "@/lib/researchTypes";

import { Section } from "./Section";
import { StageCard } from "./StageCard";

interface StrategiesTabProps {
  data: ResearchOverview;
  onOpenReport: (path: string) => void;
}

function NoteList({ notes }: { notes: { label: string; text: string }[] }) {
  return (
    <dl className="max-w-3xl space-y-3">
      {notes.map((note) => (
        <div key={note.label}>
          <dt className="text-xs font-semibold text-text-primary">{note.label}</dt>
          <dd className="mt-0.5 text-sm leading-relaxed text-text-muted">{note.text}</dd>
        </div>
      ))}
    </dl>
  );
}

export function StrategiesTab({ data, onOpenReport }: StrategiesTabProps) {
  const { baseline } = data;
  if (!baseline) {
    return <p className="text-sm text-text-muted">The baseline file could not be read. See the warnings above.</p>;
  }
  const byId = new Map(data.ideas.map((i) => [i.id, i]));

  return (
    <div>
      <Section
        title={`Baseline v${baseline.version}, adopted ${baseline.adopted_on}`}
        hint="The strategy in use at each stage. Every new idea is judged by what it adds on top of this."
      >
        <div className="grid gap-3 lg:grid-cols-3">
          {baseline.stages.map((stage) => (
            <StageCard key={stage.key} stage={stage} idea={byId.get(stage.strategy)} onOpenReport={onOpenReport} />
          ))}
        </div>
      </Section>

      <Section title="The idea behind both strategies">
        <p className="max-w-3xl text-sm leading-relaxed text-text-primary">{baseline.mechanism}</p>
      </Section>

      <Section title="Once an account is funded" hint="Sizing and payout rules locked with the baseline.">
        <NoteList notes={baseline.funded_rules} />
      </Section>

      <Section title="How a new strategy is judged" hint="A newcomer has to add money per eval on top of the baseline, not just look good alone.">
        <NoteList notes={baseline.challenger_rules} />
      </Section>
    </div>
  );
}
