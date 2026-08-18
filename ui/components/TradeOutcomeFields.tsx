"use client";

import { Input } from "@/components/ui/input";
import { BeOutcomeControl } from "@/components/TradeAssessmentPanel";

import type { BeOutcome, Trade } from "@/lib/types";
import type { TradeResult } from "@/lib/tradeEditState";

import { resultFromStatusOutcome } from "@/lib/tradeEditState";

export interface TradeOutcomeValue {
  status: Trade["status"];
  outcome: Trade["outcome"];
  exitPrice: string;
  closeTime: string;
  beOutcome: BeOutcome | null;
}

interface TradeOutcomeFieldsProps {
  value: TradeOutcomeValue;
  wasTerminal: boolean;
  error?: string | null;
  onResultChange: (result: TradeResult) => void;
  onFieldChange: <K extends keyof TradeOutcomeValue>(key: K, value: TradeOutcomeValue[K]) => void;
}

const RESULT_OPTIONS: { value: TradeResult; label: string; activeCls: string }[] = [
  { value: "open", label: "Open", activeCls: "border-border bg-surface-input text-text-primary" },
  { value: "win", label: "Win", activeCls: "border-bull text-bull bg-bull/10" },
  { value: "loss", label: "Loss", activeCls: "border-bear text-bear bg-bear/10" },
  { value: "breakeven", label: "Breakeven", activeCls: "border-breakeven text-breakeven bg-breakeven/10" },
  { value: "cancelled", label: "Cancelled", activeCls: "border-border bg-surface-input text-text-primary line-through" },
];

const INPUT_CLASS =
  "bg-surface-input border-border text-text-primary focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

export function TradeOutcomeFields({ value, wasTerminal, error, onResultChange, onFieldChange }: TradeOutcomeFieldsProps) {
  const current = resultFromStatusOutcome(value);
  const needsExit = current === "win" || current === "loss" || current === "breakeven";

  return (
    <div className="border border-border rounded p-4 space-y-3 bg-card">
      <div className="label">Result</div>

      <div className="flex flex-wrap gap-1.5">
        {RESULT_OPTIONS.map((opt) => {
          const disabled = opt.value === "open" && wasTerminal;
          const active = current === opt.value;
          return (
            <button
              key={opt.value}
              type="button"
              disabled={disabled}
              title={disabled ? "Closed trades can't be reopened — delete and re-log if this was a mistake" : undefined}
              onClick={() => onResultChange(opt.value)}
              className={`flex-1 min-w-[5.5rem] text-xs font-medium border rounded px-2 py-1.5 transition-colors ${
                active ? opt.activeCls : "border-border text-text-muted hover:text-text-primary"
              } ${disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>

      {needsExit && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="label">Exit Price</label>
            <Input
              type="number"
              step="any"
              value={value.exitPrice}
              onChange={(e) => onFieldChange("exitPrice", e.target.value)}
              placeholder="Exit price..."
              className={INPUT_CLASS}
            />
          </div>
          <div className="space-y-1">
            <label className="label">Close Time (ET)</label>
            <Input
              type="datetime-local"
              value={value.closeTime}
              onChange={(e) => onFieldChange("closeTime", e.target.value)}
              className={INPUT_CLASS}
            />
          </div>
        </div>
      )}

      {current === "breakeven" && (
        <BeOutcomeControl value={value.beOutcome} onChange={(v) => onFieldChange("beOutcome", v)} />
      )}

      {error && <p className="text-xs text-bear">{error}</p>}
    </div>
  );
}
