import { useState } from "react";

import { Input } from "@/components/ui/input";
import { DirectionToggle } from "@/components/DirectionToggle";
import { formatPrice } from "@/lib/utils";
import type { Trade } from "@/lib/types";

export interface TradeInfoValue {
  direction: "BUY" | "SELL";
  entryPrice: string;
  slPrice: string;
  tpPrice: string;
  contracts: string;
  openTime: string;
}

interface TradeInfoPanelProps {
  trade: Trade;
  value: TradeInfoValue;
  unitLabel: string;
  sizeLabel: string;
  isBacktest?: boolean;
  onChange: <K extends keyof TradeInfoValue>(key: K, value: TradeInfoValue[K]) => void;
}

const INPUT_CLASS =
  "h-7 bg-surface-input border-border text-text-primary text-right focus-visible:ring-1 focus-visible:ring-offset-0 ring-bull price";

export function TradeInfoPanel({
  trade, value, unitLabel, sizeLabel, isBacktest = false, onChange,
}: TradeInfoPanelProps) {
  const [expanded, setExpanded] = useState(false);
  const sizeFieldLabel = sizeLabel === "contracts" ? "Contracts" : "Lot Size";

  return (
    <div className="border border-border rounded p-4 space-y-3 bg-card">
      <div className="flex items-center justify-between">
        <span className="label">Trade Details</span>
        <button
          onClick={() => setExpanded((v) => !v)}
          className="text-[10px] uppercase tracking-wider text-text-muted hover:text-bull cursor-pointer transition-colors"
        >
          {expanded ? "▾ Correct trade details" : "▸ Correct trade details"}
        </button>
      </div>

      {expanded && (
        <div className="space-y-1">
          <label className="label block mb-1">Direction</label>
          <DirectionToggle value={value.direction} onChange={(v) => onChange("direction", v)} />
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2">
        <PriceRow label="Entry" value={trade.entry_price} editValue={value.entryPrice} editing={expanded} onChange={(v) => onChange("entryPrice", v)} />
        <PriceRow label="SL" value={trade.sl_price} editValue={value.slPrice} editing={expanded} onChange={(v) => onChange("slPrice", v)} />
        <PriceRow label="TP" value={trade.tp_price} editValue={value.tpPrice} editing={expanded} onChange={(v) => onChange("tpPrice", v)} placeholder="—" />
        {!isBacktest && (
          <PriceRow label={sizeFieldLabel} value={trade.contracts} editValue={value.contracts} editing={expanded} onChange={(v) => onChange("contracts", v)} />
        )}
        {!expanded && (
          <div className="flex justify-between">
            <span className="label">Risk</span>
            <span className="price text-text-primary">{trade.risk_points} {unitLabel}</span>
          </div>
        )}
        {expanded && (
          <div className="flex items-center justify-between gap-3 sm:col-span-2">
            <span className="label shrink-0">Open Time (ET)</span>
            <Input
              type="datetime-local"
              value={value.openTime}
              onChange={(e) => onChange("openTime", e.target.value)}
              className={INPUT_CLASS + " w-auto"}
            />
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */

interface PriceRowProps {
  label: string;
  value: number | null;
  editValue: string;
  editing: boolean;
  onChange: (v: string) => void;
  placeholder?: string;
}

function PriceRow({ label, value, editValue, editing, onChange, placeholder }: PriceRowProps) {
  if (!editing) {
    if (value == null && !placeholder) return null;
    return (
      <div className="flex justify-between">
        <span className="label">{label}</span>
        <span className="price text-text-primary">{value != null ? formatPrice(value) : placeholder}</span>
      </div>
    );
  }
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="label shrink-0">{label}</span>
      <Input
        type="number"
        step="any"
        value={editValue}
        onChange={(e) => onChange(e.target.value)}
        className={INPUT_CLASS}
      />
    </div>
  );
}
