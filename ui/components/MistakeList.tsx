"use client";

import { useState } from "react";

import type { Mistake } from "@/lib/types";

interface MistakeListProps {
  mistakes: Mistake[];
  onIncrement: (id: string) => void;
  onDelete: (id: string) => void;
}

const COUNT_HIGH = 10;
const COUNT_MED = 5;

function countColor(count: number): string {
  if (count >= COUNT_HIGH) return "#ef5350";
  if (count >= COUNT_MED) return "#f59e0b";
  return "#9e9e9e";
}

function countBg(count: number): string {
  if (count >= COUNT_HIGH) return "rgba(239,83,80,0.12)";
  if (count >= COUNT_MED) return "rgba(245,158,11,0.12)";
  return "rgba(158,158,158,0.12)";
}

function formatRelative(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d ago`;
  const diffMonths = Math.floor(diffDays / 30);
  return `${diffMonths}mo ago`;
}

export function MistakeList({ mistakes, onIncrement, onDelete }: MistakeListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  if (mistakes.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-sm text-muted-foreground mb-1">No mistakes tracked yet.</p>
        <p className="text-xs text-muted-foreground">
          Add the first one above — patterns you catch become patterns you fix.
        </p>
      </div>
    );
  }

  return (
    <div className="border border-border rounded overflow-hidden divide-y divide-border bg-card">
      {mistakes.map((m, i) => {
        if (deletingId === m.id) {
          return (
            <div
              key={m.id}
              className="flex items-center gap-3 px-4 py-3 bg-card"
            >
              <span className="text-xs text-muted-foreground w-6 text-right shrink-0 tabular-nums">
                #{i + 1}
              </span>
              <span className="flex-1 text-sm text-muted-foreground truncate">
                Delete &quot;{m.name}&quot;?
              </span>
              <button
                type="button"
                onClick={() => { onDelete(m.id); setDeletingId(null); }}
                className="text-xs text-bear px-2"
              >
                Yes
              </button>
              <button
                type="button"
                onClick={() => setDeletingId(null)}
                className="text-xs text-muted-foreground px-2"
              >
                No
              </button>
            </div>
          );
        }

        return (
          <div
            key={m.id}
            className="flex items-center gap-3 px-4 py-3 hover:bg-elevated transition-colors group"
          >
            <span className="text-xs text-muted-foreground w-6 text-right shrink-0 tabular-nums">
              #{i + 1}
            </span>
            <span
              className="shrink-0 min-w-[2.75rem] text-center text-xs font-mono font-semibold px-2 py-0.5 rounded tabular-nums"
              style={{ color: countColor(m.count), backgroundColor: countBg(m.count) }}
            >
              &times;{m.count}
            </span>
            <span className="flex-1 text-sm text-foreground truncate">{m.name}</span>
            <span className="text-xs text-muted-foreground shrink-0 hidden sm:block tabular-nums">
              {formatRelative(m.last_occurred_at)}
            </span>
            <button
              type="button"
              onClick={() => onIncrement(m.id)}
              aria-label={`Increment count for ${m.name}`}
              className="shrink-0 px-2 py-0.5 text-xs rounded border border-border text-muted-foreground hover:border-bull hover:text-bull transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
            >
              +1
            </button>
            <button
              type="button"
              onClick={() => setDeletingId(m.id)}
              aria-label={`Delete ${m.name}`}
              className="shrink-0 w-4 text-center text-xs text-muted-foreground hover:text-bear transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
            >
              &times;
            </button>
          </div>
        );
      })}
    </div>
  );
}
