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

const ENTRY_MODEL_OPTIONS = [
  { value: "silver_bullet", label: "Silver Bullet" },
  { value: "cisd",          label: "CISD" },
  { value: "bms",           label: "BMS" },
  { value: "ote",           label: "OTE" },
  { value: "turtle_soup",   label: "Turtle Soup" },
  { value: "other",         label: "Other" },
];

const PD_ARRAY_OPTIONS = [
  { value: "premium",     label: "Premium" },
  { value: "discount",    label: "Discount" },
  { value: "equilibrium", label: "Equilibrium" },
];

export function IctExtendedFields({ form, onChange }: IctExtendedFieldsProps) {
  return (
    <>
      {/* HTF Bias + Entry Model */}
      <div className="grid grid-cols-2 gap-3">
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
        <div>
          <label className={LABEL_CLASS}>Entry Model</label>
          <select
            className={SELECT_CLASS}
            value={form.ict_entry_model ?? ""}
            onChange={(e) => onChange("ict_entry_model", e.target.value || null)}
          >
            <option value="">Select model</option>
            {ENTRY_MODEL_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {/* P/D Array */}
      <div>
        <label className={LABEL_CLASS}>Entry Location (P/D)</label>
        <select
          className={SELECT_CLASS}
          value={form.ict_pd_array ?? ""}
          onChange={(e) => onChange("ict_pd_array", e.target.value || null)}
        >
          <option value="">Select location</option>
          {PD_ARRAY_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>
    </>
  );
}
