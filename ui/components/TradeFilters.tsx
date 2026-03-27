"use client";

import { strategies } from "@/lib/strategies";

export interface TradeFilterValues {
  strategy: string;
  symbol: string;
  status: string;
  outcome: string;
  from: string;
  to: string;
}

interface TradeFiltersProps {
  values: TradeFilterValues;
  onChange: (values: TradeFilterValues) => void;
  symbols: string[];
}

const selectClass =
  "bg-[#1e1e1e] border border-[#2a2a2a] text-sm text-[#e0e0e0] rounded px-3 py-1.5 outline-none focus:border-[#26a69a] cursor-pointer transition-colors";
const dateClass =
  "bg-[#1e1e1e] border border-[#2a2a2a] text-sm text-[#e0e0e0] rounded px-3 py-1.5 outline-none focus:border-[#26a69a] w-36 cursor-pointer transition-colors";

export function TradeFilters({ values, onChange, symbols }: TradeFiltersProps) {
  const set = (key: keyof TradeFilterValues, v: string) =>
    onChange({ ...values, [key]: v });

  const hasActive = Object.values(values).some((v) => v !== "");

  return (
    <div className="flex flex-wrap items-center gap-2 py-3">
      <select
        className={selectClass}
        value={values.strategy}
        onChange={(e) => set("strategy", e.target.value)}
      >
        <option value="">All Strategies</option>
        {strategies.map((s) => (
          <option key={s.slug} value={s.slug}>{s.label}</option>
        ))}
      </select>

      <select
        className={selectClass}
        value={values.symbol}
        onChange={(e) => set("symbol", e.target.value)}
      >
        <option value="">All Pairs</option>
        {symbols.map((s) => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      <select
        className={selectClass}
        value={values.status}
        onChange={(e) => set("status", e.target.value)}
      >
        <option value="">All Status</option>
        <option value="open">Open</option>
        <option value="closed">Closed</option>
        <option value="breakeven">Breakeven</option>
        <option value="cancelled">Cancelled</option>
      </select>

      <select
        className={selectClass}
        value={values.outcome}
        onChange={(e) => set("outcome", e.target.value)}
      >
        <option value="">All Outcomes</option>
        <option value="win">Win</option>
        <option value="loss">Loss</option>
        <option value="breakeven">Breakeven</option>
      </select>

      <input
        type="date"
        className={dateClass}
        value={values.from}
        onChange={(e) => set("from", e.target.value)}
        placeholder="From"
      />
      <input
        type="date"
        className={dateClass}
        value={values.to}
        onChange={(e) => set("to", e.target.value)}
        placeholder="To"
      />

      {hasActive && (
        <button
          type="button"
          className="text-xs text-[#777777] hover:text-[#e0e0e0] cursor-pointer transition-colors"
          onClick={() =>
            onChange({ strategy: "", symbol: "", status: "", outcome: "", from: "", to: "" })
          }
        >
          Clear all
        </button>
      )}
    </div>
  );
}
