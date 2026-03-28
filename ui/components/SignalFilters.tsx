"use client";

import type { InstrumentType } from "@/lib/types";

const FOREX_PAIRS = [
  "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
  "EURJPY", "EURGBP", "EURCHF", "EURAUD", "EURCAD", "EURNZD",
  "GBPJPY", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD",
  "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD",
  "NZDJPY", "NZDCAD", "NZDCHF",
  "CADJPY", "CADCHF", "CHFJPY",
];

const FUTURES_SYMBOLS = ["MNQ"];

export interface SignalFilterValues {
  symbol: string;
  direction: string;
  dateFrom: string;
  dateTo: string;
}

interface SignalFiltersProps {
  values: SignalFilterValues;
  onChange: (values: SignalFilterValues) => void;
  total: number;
  onReset: () => void;
  instrumentType: InstrumentType;
}

const selectClass =
  "bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-sm text-[#e0e0e0] " +
  "focus:outline-none focus:border-[#3a3a3a] appearance-none cursor-pointer min-w-[120px]";

const inputClass =
  "bg-[#1a1a1a] border border-[#2a2a2a] rounded px-2.5 py-1.5 text-sm text-[#e0e0e0] " +
  "focus:outline-none focus:border-[#3a3a3a] min-w-[130px]";

export function SignalFilters({ values, onChange, total, onReset, instrumentType }: SignalFiltersProps) {
  const update = (patch: Partial<SignalFilterValues>) =>
    onChange({ ...values, ...patch });

  const hasFilters =
    values.symbol || values.direction || values.dateFrom || values.dateTo;

  const symbols = instrumentType === "futures_mnq" ? FUTURES_SYMBOLS : FOREX_PAIRS;

  return (
    <div className="flex flex-wrap items-center gap-3">
      {/* Symbol */}
      <select
        className={selectClass}
        value={values.symbol}
        onChange={(e) => update({ symbol: e.target.value })}
      >
        <option value="">{instrumentType === "futures_mnq" ? "All Symbols" : "All Pairs"}</option>
        {symbols.map((p) => (
          <option key={p} value={p}>{p}</option>
        ))}
      </select>

      {/* Direction */}
      <select
        className={selectClass}
        value={values.direction}
        onChange={(e) => update({ direction: e.target.value })}
      >
        <option value="">Buy & Sell</option>
        <option value="BUY">BUY</option>
        <option value="SELL">SELL</option>
      </select>

      {/* Date From */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-[#777777]">From</span>
        <input
          type="date"
          className={inputClass}
          value={values.dateFrom}
          onChange={(e) => update({ dateFrom: e.target.value })}
        />
      </div>

      {/* Date To */}
      <div className="flex items-center gap-1.5">
        <span className="text-xs text-[#777777]">To</span>
        <input
          type="date"
          className={inputClass}
          value={values.dateTo}
          onChange={(e) => update({ dateTo: e.target.value })}
        />
      </div>

      {/* Result count + Reset */}
      <div className="flex items-center gap-3 ml-auto">
        <span className="text-xs text-[#777777]">
          {total} signal{total !== 1 ? "s" : ""}
        </span>
        {hasFilters && (
          <button
            onClick={onReset}
            className="text-xs text-[#777777] hover:text-[#e0e0e0] transition-colors"
          >
            Clear filters
          </button>
        )}
      </div>
    </div>
  );
}
