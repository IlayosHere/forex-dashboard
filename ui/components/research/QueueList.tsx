import type { QueueItem, QueueStatus } from "@/lib/researchTypes";

import { TonePill } from "./StatusPill";

const STATUS_TEXT: Record<QueueStatus, string> = {
  queued: "Queued",
  picked_up: "Picked up",
  answered: "Answered",
};

interface QueueListProps {
  items: QueueItem[];
}

export function QueueList({ items }: QueueListProps) {
  if (items.length === 0) {
    return <p className="text-sm text-text-muted">Nothing in the queue yet. Add the first idea above.</p>;
  }
  return (
    <div className="max-w-2xl space-y-2">
      {items.map((item) => (
        <div key={item.id} className="rounded-lg border border-border bg-surface-raised p-4">
          <div className="flex flex-wrap items-center gap-2">
            <TonePill tone={item.status === "answered" ? "good" : "neutral"}>{STATUS_TEXT[item.status]}</TonePill>
            <span className="text-sm font-medium text-text-primary">{item.title}</span>
            <span className="ml-auto text-xs text-text-dim">{item.submitted_at.slice(0, 10)}</span>
          </div>
          <p className="mt-1 text-xs text-text-dim">
            {item.kind === "note" ? `Note on ${item.about}` : "New idea"}
            {item.stage !== "any" && `, stage ${item.stage}`}
            {item.round && `, round ${item.round}`}
          </p>
          <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-text-muted">{item.body}</p>
          {item.answer && (
            <p className="mt-2 border-l-2 border-bull/50 pl-3 text-xs leading-relaxed text-text-primary">{item.answer}</p>
          )}
        </div>
      ))}
    </div>
  );
}
