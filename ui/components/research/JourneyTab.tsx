"use client";

import { useState } from "react";

import type { JourneyItem } from "@/lib/researchTypes";

import { JourneyRow } from "./JourneyRow";

type KindFilter = "all" | JourneyItem["kind"];

const FILTERS: { key: KindFilter; label: string }[] = [
  { key: "all", label: "Everything" },
  { key: "decision", label: "Decisions" },
  { key: "trial", label: "Trials" },
  { key: "exploration", label: "Looks" },
];

interface JourneyTabProps {
  journey: JourneyItem[];
}

export function JourneyTab({ journey }: JourneyTabProps) {
  const [kind, setKind] = useState<KindFilter>("all");
  const items = journey.filter((j) => kind === "all" || j.kind === kind);

  return (
    <div>
      <p className="mb-3 max-w-3xl text-xs leading-relaxed text-text-muted">
        Every decision, trial and counted look, newest first. Click a line to read the reasoning.
      </p>
      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            aria-pressed={kind === f.key}
            onClick={() => setKind(f.key)}
            className={`rounded-full border px-3 py-1 text-xs ${
              kind === f.key ? "border-border-light bg-elevated text-text-primary" : "border-border text-text-muted hover:text-text-primary"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>
      <div className="rounded-lg border border-border bg-surface-raised px-4">
        {items.map((item) => (
          <JourneyRow key={`${item.kind}-${item.date}-${item.title}`} item={item} />
        ))}
        {items.length === 0 && <p className="py-4 text-sm text-text-muted">Nothing here yet.</p>}
      </div>
    </div>
  );
}
