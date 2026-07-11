"use client";

import { strategies } from "@/lib/strategies";
import { Combobox } from "@/components/ui/combobox";

import type { InstrumentType, Account } from "@/lib/types";
import type { PresetKey, UseStatsContextResult } from "@/lib/useStatsContext";

const INSTRUMENT_OPTIONS: { value: InstrumentType | ""; label: string }[] = [
  { value: "futures", label: "Futures" },
  { value: "",        label: "All" },
];

const PRESETS: { key: PresetKey; label: string }[] = [
  { key: "7d", label: "7D" },
  { key: "30d", label: "30D" },
  { key: "month", label: "MTD" },
  { key: "3m", label: "3M" },
  { key: "all", label: "All" },
];

const FEELING_OPTIONS = [
  { value: "", label: "All Feelings" },
  { value: "calm", label: "Calm" },
  { value: "focused", label: "Focused" },
  { value: "confident", label: "Confident" },
  { value: "anxious", label: "Anxious" },
  { value: "impatient", label: "Impatient" },
  { value: "fearful", label: "Fearful" },
  { value: "greedy", label: "Greedy" },
  { value: "distracted", label: "Distracted" },
  { value: "revenge", label: "Revenge" },
  { value: "tired", label: "Tired" },
];

const SELECT_CLS = "bg-surface-input border border-border rounded px-2 py-1 text-xs text-text-primary focus:outline-none focus:border-bull";

function InstrumentPills({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-0 rounded-md overflow-hidden border border-border">
      {INSTRUMENT_OPTIONS.map((opt, i) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`px-3 py-1 text-xs font-medium transition-colors ${
            i < INSTRUMENT_OPTIONS.length - 1 ? "border-r border-border" : ""
          } ${
            value === opt.value
              ? "bg-bull/10 text-bull"
              : "text-text-muted hover:text-text-primary"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

function PresetPills({ value, hasCustom, onChange }: { value: PresetKey; hasCustom: boolean; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-1">
      {PRESETS.map((p) => {
        const active = value === p.key && !hasCustom;
        return (
          <button
            key={p.key}
            type="button"
            onClick={() => onChange(p.key)}
            className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
              active
                ? "border-bull text-bull bg-bull/10"
                : "border-border text-text-muted hover:text-text-primary"
            }`}
          >
            {p.label}
          </button>
        );
      })}
    </div>
  );
}

interface ContextBarProps {
  ctx: UseStatsContextResult;
  accounts: Account[];
}

export function ContextBar({ ctx, accounts }: ContextBarProps) {
  const { context, setFilter, setBacktestMode, resetFilters, ribbonText, isDefault } = ctx;
  const hasCustom = !!(context.customFrom || context.customTo);

  return (
    <div className="mb-5">
      <div className="flex flex-wrap items-center gap-3 mb-2">
        <div className="flex h-7 rounded border border-border bg-surface-input p-0.5 gap-0.5">
          {(["Live", "Backtest"] as const).map((label) => {
            const active = label === "Backtest" ? context.backtestMode : !context.backtestMode;
            return (
              <button
                key={label}
                type="button"
                onClick={() => {
                    const next = label === "Backtest";
                    setBacktestMode(next);
                    if (context.accountId) {
                      const acct = accounts.find((a) => a.id === context.accountId);
                      if (acct && (next ? acct.account_type !== "backtest" : acct.account_type === "backtest")) {
                        setFilter("accountId", "");
                      }
                    }
                  }}
                className={`px-3 rounded-sm text-xs font-medium transition-colors cursor-pointer ${
                  active
                    ? "bg-bull/20 text-bull ring-1 ring-inset ring-bull/40"
                    : "text-text-dim hover:text-text-muted"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>

        <InstrumentPills
          value={context.instrumentType}
          onChange={(v) => setFilter("instrumentType", v)}
        />

        <Combobox
          value={context.accountId}
          onChange={(v) => setFilter("accountId", v ?? "")}
          aria-label="Filter by account"
          className="w-auto h-7 text-xs px-2 py-1"
          options={[{ value: "", label: "All Accounts" }, ...accounts.map((a) => ({ value: a.id, label: a.name }))]}
        />

        <Combobox
          value={context.strategy}
          onChange={(v) => setFilter("strategy", v ?? "")}
          aria-label="Filter by strategy"
          className="w-auto h-7 text-xs px-2 py-1"
          options={[{ value: "", label: "All Strategies" }, ...strategies.map((s) => ({ value: s.slug, label: s.label }))]}
        />

        {!context.backtestMode && (
          <Combobox
            value={context.feelingBefore}
            onChange={(v) => setFilter("feelingBefore", v ?? "")}
            aria-label="Filter by feeling before trade"
            className="w-auto h-7 text-xs px-2 py-1"
            options={FEELING_OPTIONS}
          />
        )}

        <PresetPills
          value={context.preset}
          hasCustom={hasCustom}
          onChange={(v) => setFilter("preset", v)}
        />

        <div className="flex items-center gap-1 ml-auto">
          <input
            type="date"
            value={context.customFrom}
            onChange={(e) => setFilter("customFrom", e.target.value)}
            aria-label="From date"
            className={SELECT_CLS}
          />
          <span className="text-text-dim text-xs">→</span>
          <input
            type="date"
            value={context.customTo}
            onChange={(e) => setFilter("customTo", e.target.value)}
            aria-label="To date"
            className={SELECT_CLS}
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className={`text-xs ${isDefault ? "text-text-dim" : "text-text-muted"}`}>
          Viewing: {ribbonText}
        </span>
        {!isDefault && (
          <button
            type="button"
            onClick={resetFilters}
            className="text-xs text-bull hover:text-bull/70 underline"
          >
            Reset
          </button>
        )}
      </div>
    </div>
  );
}
