import type { QueueItem, ResearchIdea } from "@/lib/researchTypes";

import { IdeaForm } from "./IdeaForm";
import { QueueList } from "./QueueList";
import { Section } from "./Section";

interface YourIdeasTabProps {
  ideas: ResearchIdea[];
  queue: QueueItem[];
  onSaved: () => void;
}

export function YourIdeasTab({ ideas, queue, onSaved }: YourIdeasTabProps) {
  return (
    <div>
      <Section title="Add to the research" hint="Your ideas go into the queue for the next exploration round. Check the Ideas tab first: if something similar was already tested, add a note to it instead.">
        <IdeaForm ideas={ideas} onSaved={onSaved} />
      </Section>
      <Section title="Your queue" hint="Newest first. The status changes when a round picks the item up and when it is answered.">
        <QueueList items={queue} />
      </Section>
    </div>
  );
}
