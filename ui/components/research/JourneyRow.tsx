import type { JourneyItem } from "@/lib/researchTypes";

const KIND_LABEL: Record<JourneyItem["kind"], string> = {
  decision: "Decision",
  trial: "Trial",
  exploration: "Look",
};

const KIND_DOT: Record<JourneyItem["kind"], string> = {
  decision: "bg-accent-gold",
  trial: "bg-bull",
  exploration: "bg-breakeven",
};

interface JourneyRowProps {
  item: JourneyItem;
}

/** One line on the timeline; click to read the detail. */
export function JourneyRow({ item }: JourneyRowProps) {
  return (
    <details className="group border-b border-border py-2.5 last:border-b-0">
      <summary className="flex cursor-pointer list-none items-start gap-3">
        <span className="w-20 shrink-0 pt-0.5 font-mono text-xs text-text-dim">{item.date}</span>
        <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${KIND_DOT[item.kind]}`} aria-hidden />
        <span className="min-w-0 flex-1">
          <span className="mr-2 text-xs uppercase tracking-wide text-text-dim">{KIND_LABEL[item.kind]}</span>
          <span className="text-sm text-text-primary">{item.title}</span>
        </span>
      </summary>
      {item.detail && (
        <p className="mt-2 ml-[6.25rem] max-w-3xl text-xs leading-relaxed text-text-muted">{item.detail}</p>
      )}
    </details>
  );
}
