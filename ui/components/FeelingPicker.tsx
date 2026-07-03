"use client";

import { FEELING_OPTIONS } from "@/lib/feelings";

import type { TradingFeeling } from "@/lib/types";

interface FeelingPickerProps {
  value: TradingFeeling | null;
  onChange: (value: TradingFeeling | null) => void;
  disabled?: boolean;
  /** Smaller hit targets for a secondary occurrence of the same control on one page. */
  compact?: boolean;
}

export function FeelingPicker({ value, onChange, disabled = false, compact = false }: FeelingPickerProps) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {FEELING_OPTIONS.map((opt) => {
        const isActive = value === opt.value;
        const activeColor = opt.sentiment === "positive" ? "#26a69a" : "#ef5350";
        return (
          <button
            key={opt.value}
            type="button"
            disabled={disabled}
            onClick={() => onChange(isActive ? null : opt.value)}
            className={`rounded font-medium border transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
              compact ? "px-1.5 py-0.5 text-[10px]" : "px-2 py-1 text-[11px]"
            } ${
              isActive
                ? "border-current"
                : "border-border text-text-muted hover:border-[#444] hover:text-text-primary"
            }`}
            style={isActive ? { color: activeColor, backgroundColor: `${activeColor}18` } : undefined}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
}
