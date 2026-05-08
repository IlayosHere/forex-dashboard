"use client";

import { FeelingPicker } from "@/components/FeelingPicker";

import type { TradingFeeling } from "@/lib/types";

const LABEL_CLASS = "text-[10px] uppercase tracking-widest text-text-muted w-14 shrink-0 pt-1";

interface TradeFeelingsPanelProps {
  feelingBefore: TradingFeeling | null;
  feelingDuring: TradingFeeling | null;
  feelingAfter: TradingFeeling | null;
  onChange: (field: "feeling_before" | "feeling_during" | "feeling_after", value: TradingFeeling | null) => void;
  disabled?: boolean;
}

export function TradeFeelingsPanel({
  feelingBefore,
  feelingDuring,
  feelingAfter,
  onChange,
  disabled = false,
}: TradeFeelingsPanelProps) {
  return (
    <div className="border border-border rounded-lg p-4 bg-card">
      <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
        Feelings
      </h3>
      <div className="flex flex-col gap-3">
        <div className="flex gap-3 items-start">
          <span className={LABEL_CLASS}>Before</span>
          <FeelingPicker value={feelingBefore} onChange={(v) => onChange("feeling_before", v)} disabled={disabled} />
        </div>
        <div className="flex gap-3 items-start">
          <span className={LABEL_CLASS}>During</span>
          <FeelingPicker value={feelingDuring} onChange={(v) => onChange("feeling_during", v)} disabled={disabled} />
        </div>
        <div className="flex gap-3 items-start">
          <span className={LABEL_CLASS}>After</span>
          <FeelingPicker value={feelingAfter} onChange={(v) => onChange("feeling_after", v)} disabled={disabled} />
        </div>
      </div>
    </div>
  );
}
