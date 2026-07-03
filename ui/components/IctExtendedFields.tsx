"use client";

import { Combobox } from "@/components/ui/combobox";

import type { TradeFormData } from "./TradeForm";

interface IctExtendedFieldsProps {
  form: TradeFormData;
  onChange: <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) => void;
}

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
        <Combobox
          options={HTF_BIAS_OPTIONS}
          value={form.ict_htf_bias ?? null}
          onChange={(v) => onChange("ict_htf_bias", v)}
          placeholder="Select bias"
          filterable={false}
        />
      </div>
    </>
  );
}
