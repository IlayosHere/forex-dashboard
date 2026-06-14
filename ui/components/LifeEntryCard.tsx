"use client";

import { MOOD_CONFIG } from "@/lib/moodConfig";
import type { LifeEntry } from "@/lib/types";

interface LifeEntryCardProps {
  entry: LifeEntry;
  onClick: () => void;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function LifeEntryCard({ entry, onClick }: LifeEntryCardProps) {
  const moodCfg = entry.mood ? MOOD_CONFIG[entry.mood] : null;
  const accentColor = moodCfg?.color ?? "transparent";
  const showLabel = entry.tags.length === 0;

  return (
    <div
      onClick={onClick}
      data-interactive
      className="cursor-pointer px-4 py-3 border-l-2 bg-surface hover:bg-elevated transition-colors"
      style={{ borderLeftColor: accentColor }}
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm text-text-primary line-clamp-2 flex-1 min-w-0">{entry.body}</p>
        <span className="text-xs text-text-muted shrink-0">{formatTime(entry.entry_at)}</span>
      </div>

      {(moodCfg || entry.tags.length > 0) && (
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          {moodCfg && (
            <span className="text-xs font-medium" style={{ color: moodCfg.color }}>
              {moodCfg.emoji}{showLabel ? ` ${moodCfg.label}` : ""}
            </span>
          )}
          {entry.tags.map((tag) => (
            <span
              key={tag}
              className="text-[10px] bg-elevated text-text-muted rounded-full px-2 py-0.5"
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
