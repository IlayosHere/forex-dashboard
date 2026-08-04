"use client";

import { useMemo } from "react";
import { strategies } from "@/lib/strategies";
import { Combobox } from "@/components/ui/combobox";
import { IFVG_TF_OPTIONS } from "@/components/IctParamsPanel";
import type { Account, InstrumentType } from "@/lib/types";

export interface TradeFilterValues {
  account_id: string;
  strategy: string;
  symbol: string;
  status: string;
  outcome: string;
  rule_followed: string;
  ict_ifvg_timeframe: string;
  from: string;
  to: string;
}

interface TradeFiltersProps {
  values: TradeFilterValues;
  onChange: (values: TradeFilterValues) => void;
  symbols: string[];
  accounts: Account[];
  instrumentType: InstrumentType;
}

const comboClass = "w-auto min-w-36 max-w-56 h-8";
const dateClass =
  "bg-[#1e1e1e] border border-[#2a2a2a] text-sm text-[#e0e0e0] rounded px-3 py-1.5 outline-none focus:border-[#26a69a] w-36 cursor-pointer transition-colors";

export function TradeFilters({ values, onChange, symbols, accounts, instrumentType }: TradeFiltersProps) {
  const set = (key: keyof TradeFilterValues, v: string) =>
    onChange({ ...values, [key]: v });

  const hasActive = Object.values(values).some((v) => v !== "");

  const scopedStrategies = useMemo(
    () => strategies.filter((s) =>
      s.instrumentType === instrumentType ||
      (instrumentType === "futures" && s.instrumentType.startsWith("futures")),
    ),
    [instrumentType],
  );

  return (
    <div className="flex flex-wrap items-center gap-2 py-3">
      <Combobox
        className={comboClass}
        options={[{ value: "", label: "All Accounts" }, ...accounts.map((a) => ({ value: a.id, label: `${a.name} (${a.account_type})` }))]}
        value={values.account_id}
        onChange={(v) => set("account_id", v ?? "")}
      />

      <Combobox
        className={comboClass}
        options={[{ value: "", label: "All Strategies" }, ...scopedStrategies.map((s) => ({ value: s.slug, label: s.label }))]}
        value={values.strategy}
        onChange={(v) => set("strategy", v ?? "")}
      />

      <Combobox
        className={comboClass}
        options={[{ value: "", label: "All Pairs" }, ...symbols.map((s) => ({ value: s, label: s }))]}
        value={values.symbol}
        onChange={(v) => set("symbol", v ?? "")}
      />

      <Combobox
        className={comboClass}
        filterable={false}
        options={[
          { value: "", label: "All Status" },
          { value: "open", label: "Open" },
          { value: "closed", label: "Closed" },
          { value: "breakeven", label: "Breakeven" },
          { value: "cancelled", label: "Cancelled" },
        ]}
        value={values.status}
        onChange={(v) => set("status", v ?? "")}
      />

      <Combobox
        className={comboClass}
        filterable={false}
        options={[
          { value: "", label: "All Outcomes" },
          { value: "win", label: "Win" },
          { value: "loss", label: "Loss" },
          { value: "breakeven", label: "Breakeven" },
        ]}
        value={values.outcome}
        onChange={(v) => set("outcome", v ?? "")}
      />

      <Combobox
        className={comboClass}
        filterable={false}
        options={[
          { value: "", label: "All" },
          { value: "true", label: "Followed Rules" },
          { value: "false", label: "Had Mistakes" },
          { value: "null", label: "Not Reviewed" },
        ]}
        value={values.rule_followed}
        onChange={(v) => set("rule_followed", v ?? "")}
      />

      <Combobox
        className={comboClass}
        filterable={false}
        options={[
          { value: "", label: "All IFVG TF" },
          ...IFVG_TF_OPTIONS.map((tf) => ({ value: tf, label: tf.toUpperCase() })),
        ]}
        value={values.ict_ifvg_timeframe}
        onChange={(v) => set("ict_ifvg_timeframe", v ?? "")}
      />

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
            onChange({ account_id: "", strategy: "", symbol: "", status: "", outcome: "", rule_followed: "", ict_ifvg_timeframe: "", from: "", to: "" })
          }
        >
          Clear all
        </button>
      )}
    </div>
  );
}
