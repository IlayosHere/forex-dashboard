"use client";

import { LIFE_MOODS, MOOD_CONFIG } from "@/lib/moodConfig";
import type { LifeMood } from "@/lib/types";

interface LifeMoodPickerProps {
  value: LifeMood | null;
  onChange: (value: LifeMood | null) => void;
  disabled?: boolean;
}

export function LifeMoodPicker({ value, onChange, disabled = false }: LifeMoodPickerProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {LIFE_MOODS.map((mood) => {
        const cfg = MOOD_CONFIG[mood];
        const isActive = value === mood;
        return (
          <button
            key={mood}
            type="button"
            disabled={disabled}
            onClick={() => onChange(isActive ? null : mood)}
            className={`px-2 py-1 rounded text-[11px] font-medium border transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
              isActive
                ? "border-current"
                : "border-border text-text-muted hover:border-[#444] hover:text-text-primary"
            }`}
            style={isActive ? { color: cfg.color, backgroundColor: `${cfg.color}18` } : undefined}
            title={cfg.label}
          >
            {cfg.emoji} {cfg.label}
          </button>
        );
      })}
    </div>
  );
}
