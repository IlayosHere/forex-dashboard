"use client";

import { strategies } from "@/lib/strategies";

import type { InstrumentType } from "@/lib/types";

const INSTRUMENT_TABS: { value: InstrumentType | ""; label: string }[] = [
  { value: "", label: "All" },
  { value: "forex", label: "Forex" },
  { value: "futures_mnq", label: "MNQ" },
];

interface StatsFiltersProps {
  instrumentType: InstrumentType | "";
  onInstrumentChange: (v: InstrumentType | "") => void;
  strategy: string;
  onStrategyChange: (v: string) => void;
  accountId: string;
  onAccountChange: (v: string) => void;
  accounts: { id: string; name: string }[];
  from: string;
  onFromChange: (v: string) => void;
  to: string;
  onToChange: (v: string) => void;
}

export function StatsFilters({
  instrumentType, onInstrumentChange,
  strategy, onStrategyChange,
  accountId, onAccountChange, accounts,
  from, onFromChange,
  to, onToChange,
}: StatsFiltersProps) {
  return (
    <div className="mb-6">
      {/* Instrument tabs */}
      <div className="flex gap-0 mb-3 border-b border-[#2a2a2a]">
        {INSTRUMENT_TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => onInstrumentChange(tab.value as InstrumentType | "")}
            className={`px-4 py-2 text-sm font-medium transition-colors cursor-pointer -mb-px ${
              instrumentType === tab.value
                ? "text-[#26a69a] border-b-2 border-[#26a69a]"
                : "text-[#777777] hover:text-[#e0e0e0] border-b-2 border-transparent"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Dropdowns + date range */}
      <div className="flex flex-wrap gap-3">
        <select
          value={strategy}
          onChange={(e) => onStrategyChange(e.target.value)}
          aria-label="Filter by strategy"
          className="bg-[#1e1e1e] border border-[#2a2a2a] rounded px-3 py-1.5 text-sm text-[#e0e0e0] focus:outline-none focus:border-[#26a69a]"
        >
          <option value="">All Strategies</option>
          {strategies.map((s) => (
            <option key={s.slug} value={s.slug}>{s.label}</option>
          ))}
        </select>

        <select
          value={accountId}
          onChange={(e) => onAccountChange(e.target.value)}
          aria-label="Filter by account"
          className="bg-[#1e1e1e] border border-[#2a2a2a] rounded px-3 py-1.5 text-sm text-[#e0e0e0] focus:outline-none focus:border-[#26a69a]"
        >
          <option value="">All Accounts</option>
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>

        <input
          type="date"
          value={from}
          onChange={(e) => onFromChange(e.target.value)}
          placeholder="From"
          aria-label="From date"
          className="bg-[#1e1e1e] border border-[#2a2a2a] rounded px-3 py-1.5 text-sm text-[#e0e0e0] focus:outline-none focus:border-[#26a69a]"
        />
        <input
          type="date"
          value={to}
          onChange={(e) => onToChange(e.target.value)}
          placeholder="To"
          aria-label="To date"
          className="bg-[#1e1e1e] border border-[#2a2a2a] rounded px-3 py-1.5 text-sm text-[#e0e0e0] focus:outline-none focus:border-[#26a69a]"
        />
      </div>
    </div>
  );
}
