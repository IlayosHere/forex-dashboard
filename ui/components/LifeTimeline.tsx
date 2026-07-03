"use client";

import { useRouter } from "next/navigation";

import { LifeEntryCard } from "@/components/LifeEntryCard";

import type { LifeEntry } from "@/lib/types";

interface LifeTimelineProps {
  entries: LifeEntry[];
}

function groupByDay(entries: LifeEntry[]): [string, LifeEntry[]][] {
  const map = new Map<string, LifeEntry[]>();
  for (const e of entries) {
    const day = e.entry_at.slice(0, 10);
    if (!map.has(day)) map.set(day, []);
    map.get(day)!.push(e);
  }
  return Array.from(map.entries());
}

function formatDayLabel(isoDate: string): string {
  const d = new Date(`${isoDate}T12:00:00`);
  return d.toLocaleDateString([], { weekday: "long", month: "long", day: "numeric" });
}

export function LifeTimeline({ entries }: LifeTimelineProps) {
  const router = useRouter();
  const groups = groupByDay(entries);

  if (groups.length === 0) {
    return (
      <div className="text-center py-8 space-y-1">
        <p className="text-text-muted text-sm">
          No entries yet — write your first one above.
        </p>
        <p className="text-text-dim text-xs">
          Add a mood and it&apos;ll appear on your calendar heatmap.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {groups.map(([day, dayEntries]) => (
        <div key={day}>
          <div className="flex items-center justify-between mb-2 px-1">
            <p className="text-xs font-medium text-text-primary uppercase tracking-wide">
              {formatDayLabel(day)}
            </p>
            <span className="text-xs text-text-dim">
              {dayEntries.length} {dayEntries.length === 1 ? "entry" : "entries"}
            </span>
          </div>
          <div className="space-y-px rounded-lg overflow-hidden border border-border">
            {dayEntries.map((entry) => (
              <LifeEntryCard
                key={entry.id}
                entry={entry}
                onClick={() => router.push(`/life/${entry.id}`)}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
