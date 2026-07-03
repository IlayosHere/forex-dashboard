"use client";

import { Combobox } from "@/components/ui/combobox";

import { IctExtendedFields } from "./IctExtendedFields";

import type { TradeFormData } from "./TradeForm";

interface IctTradeFieldsProps {
  form: TradeFormData;
  errors: Record<string, boolean>;
  onChange: <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) => void;
}

const LABEL_CLASS = "block text-xs text-text-muted mb-1";

function errBorder(errors: Record<string, boolean>, field: string): string {
  return errors[field] ? "border-bear" : "";
}

function ErrMsg({ errors, field }: { errors: Record<string, boolean>; field: string }) {
  if (!errors[field]) return null;
  return <p className="text-bear text-xs mt-1">Required</p>;
}

const SETUP_DETAIL_OPTIONS: Record<string, { value: string; label: string }[]> = {
  liquidity_sweep: [
    { value: "london_high", label: "London High" },
    { value: "london_low", label: "London Low" },
    { value: "asia_high", label: "Asia High" },
    { value: "asia_low", label: "Asia Low" },
    { value: "data_high", label: "Data High" },
    { value: "data_low", label: "Data Low" },
    { value: "1m_high", label: "1M High" },
    { value: "1m_low", label: "1M Low" },
    { value: "5m_high", label: "5M High" },
    { value: "5m_low", label: "5M Low" },
    { value: "15m_high", label: "15M High" },
    { value: "15m_low", label: "15M Low" },
    { value: "1h_high", label: "1H High" },
    { value: "1h_low", label: "1H Low" },
    { value: "4h_high", label: "4H High" },
    { value: "4h_low", label: "4H Low" },
    { value: "1d_high", label: "1D High" },
    { value: "1d_low", label: "1D Low" },
    { value: "gap_fill", label: "Gap Fill" },
    { value: "other", label: "Other" },
  ],
  unmitigated_fvg: [
    { value: "15m", label: "15M FVG" },
    { value: "30m", label: "30M FVG" },
    { value: "1h", label: "1H FVG" },
    { value: "2h", label: "2H FVG" },
    { value: "4h", label: "4H FVG" },
    { value: "other", label: "Other" },
  ],
  continuation: [
    { value: "3m", label: "3M FVG" },
    { value: "5m", label: "5M FVG" },
    { value: "15m", label: "15M FVG" },
    { value: "other", label: "Other" },
  ],
};

const SETUP_DETAIL_LABEL: Record<string, string> = {
  liquidity_sweep: "Liquidity Level Swept",
  unmitigated_fvg: "FVG Timeframe",
  continuation: "Continuation FVG Timeframe",
};

const TP_TARGET_OPTIONS = [
  { value: "london_high", label: "London High" },
  { value: "london_low", label: "London Low" },
  { value: "asia_high", label: "Asia High" },
  { value: "asia_low", label: "Asia Low" },
  { value: "data_high", label: "Data High" },
  { value: "data_low", label: "Data Low" },
  { value: "1m_high", label: "1M High" },
  { value: "1m_low", label: "1M Low" },
  { value: "5m_high", label: "5M High" },
  { value: "5m_low", label: "5M Low" },
  { value: "15m_high", label: "15M High" },
  { value: "15m_low", label: "15M Low" },
  { value: "1h_high", label: "1H High" },
  { value: "1h_low", label: "1H Low" },
  { value: "4h_high", label: "4H High" },
  { value: "4h_low", label: "4H Low" },
  { value: "1d_high", label: "1D High" },
  { value: "1d_low", label: "1D Low" },
  { value: "unmitigated_5m_fvg", label: "Unmitigated 5M FVG" },
  { value: "unmitigated_15m_fvg", label: "Unmitigated 15M FVG" },
  { value: "unmitigated_30m_fvg", label: "Unmitigated 30M FVG" },
  { value: "unmitigated_1h_fvg", label: "Unmitigated 1H FVG" },
  { value: "unmitigated_4h_fvg", label: "Unmitigated 4H FVG" },
  { value: "ath", label: "ATH" },
  { value: "other", label: "Other" },
];

const IFVG_TF_OPTIONS = ["30s","1m","2m","3m","4m","5m"];

const SETUP_TYPE_OPTIONS = [
  { value: "liquidity_sweep", label: "Liquidity Sweep" },
  { value: "unmitigated_fvg", label: "Unmitigated FVG" },
  { value: "continuation", label: "Continuation" },
  { value: "other", label: "Other" },
];

const YES_NO_OPTIONS = [
  { value: "true", label: "Yes" },
  { value: "false", label: "No" },
];

export function IctTradeFields({ form, errors, onChange }: IctTradeFieldsProps) {
  const setupDetailOptions = form.ict_setup_type
    ? SETUP_DETAIL_OPTIONS[form.ict_setup_type] ?? []
    : [];
  const setupDetailLabel = form.ict_setup_type
    ? SETUP_DETAIL_LABEL[form.ict_setup_type] ?? "Setup Detail"
    : "Setup Detail";

  const handleSetupTypeChange = (value: string) => {
    onChange("ict_setup_type", value);
    onChange("ict_setup_detail", ""); // reset detail when type changes
  };

  return (
    <div className="space-y-4 border border-border rounded-md p-4">
      <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">ICT Setup</p>

      {/* Setup Type */}
      <div>
        <label className={LABEL_CLASS}>Setup Type *</label>
        <Combobox
          className={errBorder(errors, "ict_setup_type")}
          options={SETUP_TYPE_OPTIONS}
          value={form.ict_setup_type || null}
          onChange={(v) => handleSetupTypeChange(v ?? "")}
          placeholder="Select setup type"
          filterable={false}
        />
        <ErrMsg errors={errors} field="ict_setup_type" />
      </div>

      {/* Setup Detail — context-sensitive */}
      {form.ict_setup_type && (
        <div>
          <label className={LABEL_CLASS}>{setupDetailLabel} *</label>
          <Combobox
            className={errBorder(errors, "ict_setup_detail")}
            options={setupDetailOptions}
            value={form.ict_setup_detail || null}
            onChange={(v) => onChange("ict_setup_detail", v ?? "")}
          />
          <ErrMsg errors={errors} field="ict_setup_detail" />
        </div>
      )}

      {/* TP Target */}
      <div>
        <label className={LABEL_CLASS}>TP Target *</label>
        <Combobox
          className={errBorder(errors, "ict_tp_target")}
          options={TP_TARGET_OPTIONS}
          value={form.ict_tp_target || null}
          onChange={(v) => onChange("ict_tp_target", v ?? "")}
          placeholder="Select target"
        />
        <ErrMsg errors={errors} field="ict_tp_target" />
      </div>

      {/* IFVG Timeframe + Bars to IFVG — side by side */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={LABEL_CLASS}>IFVG Entry Timeframe *</label>
          <Combobox
            className={errBorder(errors, "ict_ifvg_timeframe")}
            options={IFVG_TF_OPTIONS.map((tf) => ({ value: tf, label: tf.toUpperCase() }))}
            value={form.ict_ifvg_timeframe || null}
            onChange={(v) => onChange("ict_ifvg_timeframe", v ?? "")}
            placeholder="Select TF"
            filterable={false}
          />
          <ErrMsg errors={errors} field="ict_ifvg_timeframe" />
        </div>
        <div>
          <label className={LABEL_CLASS}>Bars to IFVG</label>
          <input
            type="number"
            min={1}
            max={100}
            placeholder="e.g. 2"
            className={`bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull w-full h-8 transition-colors [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none`}
            value={form.ict_ifvg_bars ?? ""}
            onChange={(e) => onChange("ict_ifvg_bars", e.target.value === "" ? null : Number(e.target.value))}
          />
        </div>
      </div>

      <IctExtendedFields form={form} onChange={onChange} />

      {/* SMT + TDO + CISD — side by side */}
      <div className="grid grid-cols-3 gap-3">
        <div>
          <label className={LABEL_CLASS}>SMT Present *</label>
          <Combobox
            className={errBorder(errors, "ict_smt_present")}
            options={YES_NO_OPTIONS}
            value={form.ict_smt_present === null || form.ict_smt_present === undefined ? null : String(form.ict_smt_present)}
            onChange={(v) => onChange("ict_smt_present", v === null ? null : v === "true")}
            placeholder="Select"
            filterable={false}
          />
          <ErrMsg errors={errors} field="ict_smt_present" />
        </div>
        <div>
          <label className={LABEL_CLASS}>TDO Aligned *</label>
          <Combobox
            className={errBorder(errors, "ict_tdo_aligned")}
            options={YES_NO_OPTIONS}
            value={form.ict_tdo_aligned === null || form.ict_tdo_aligned === undefined ? null : String(form.ict_tdo_aligned)}
            onChange={(v) => onChange("ict_tdo_aligned", v === null ? null : v === "true")}
            placeholder="Select"
            filterable={false}
          />
          <ErrMsg errors={errors} field="ict_tdo_aligned" />
        </div>
        <div>
          <label className={LABEL_CLASS}>CISD Present *</label>
          <Combobox
            className={errBorder(errors, "ict_cisd_present")}
            options={YES_NO_OPTIONS}
            value={form.ict_cisd_present === null || form.ict_cisd_present === undefined ? null : String(form.ict_cisd_present)}
            onChange={(v) => onChange("ict_cisd_present", v === null ? null : v === "true")}
            placeholder="Select"
            filterable={false}
          />
          <ErrMsg errors={errors} field="ict_cisd_present" />
        </div>
      </div>
    </div>
  );
}
