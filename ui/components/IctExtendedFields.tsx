"use client";

import type { TradeFormData } from "./TradeForm";

interface IctExtendedFieldsProps {
  form: TradeFormData;
  onChange: <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) => void;
}

const SELECT_CLASS =
  "bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull w-full h-8 cursor-pointer transition-colors";

const LABEL_CLASS = "block text-xs text-text-muted mb-1";

const HTF_BIAS_OPTIONS = [
  { value: "aligned", label: "Aligned" },
  { value: "counter", label: "Counter" },
  { value: "neutral", label: "Neutral" },
];

export function IctExtendedFields({ form, onChange }: IctExtendedFieldsProps) {
  return (
    <>
      {/* HTF Bias */}
      <div>
        <label className={LABEL_CLASS}>HTF Bias</label>
        <select
          className={SELECT_CLASS}
          value={form.ict_htf_bias ?? ""}
          onChange={(e) => onChange("ict_htf_bias", e.target.value || null)}
        >
          <option value="">Select bias</option>
          {HTF_BIAS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>
    </>
  );
}
