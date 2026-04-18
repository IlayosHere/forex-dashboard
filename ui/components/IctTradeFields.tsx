"use client";

import type { TradeFormData } from "./TradeForm";

interface IctTradeFieldsProps {
  form: TradeFormData;
  errors: Record<string, boolean>;
  onChange: <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) => void;
}

const SELECT_CLASS =
  "bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull w-full h-8 cursor-pointer transition-colors";

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
    { value: "other", label: "Other" },
  ],
  unmitigated_fvg: [
    { value: "15m", label: "15M FVG" },
    { value: "1h", label: "1H FVG" },
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
  { value: "unmitigated_5m_fvg", label: "Unmitigated 5M FVG" },
  { value: "unmitigated_15m_fvg", label: "Unmitigated 15M FVG" },
  { value: "unmitigated_1h_fvg", label: "Unmitigated 1H FVG" },
  { value: "unmitigated_4h_fvg", label: "Unmitigated 4H FVG" },
  { value: "other", label: "Other" },
];

const IFVG_TF_OPTIONS = ["1m","2m","3m","4m","5m","6m","7m","8m","9m","10m","15m","other"];

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
        <select
          className={`${SELECT_CLASS} ${errBorder(errors, "ict_setup_type")}`}
          value={form.ict_setup_type ?? ""}
          onChange={(e) => handleSetupTypeChange(e.target.value)}
        >
          <option value="">Select setup type</option>
          <option value="liquidity_sweep">Liquidity Sweep</option>
          <option value="unmitigated_fvg">Unmitigated FVG</option>
          <option value="continuation">Continuation</option>
          <option value="other">Other</option>
        </select>
        <ErrMsg errors={errors} field="ict_setup_type" />
      </div>

      {/* Setup Detail — context-sensitive */}
      {form.ict_setup_type && (
        <div>
          <label className={LABEL_CLASS}>{setupDetailLabel} *</label>
          <select
            className={`${SELECT_CLASS} ${errBorder(errors, "ict_setup_detail")}`}
            value={form.ict_setup_detail ?? ""}
            onChange={(e) => onChange("ict_setup_detail", e.target.value)}
          >
            <option value="">Select...</option>
            {setupDetailOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
          <ErrMsg errors={errors} field="ict_setup_detail" />
        </div>
      )}

      {/* TP Target */}
      <div>
        <label className={LABEL_CLASS}>TP Target *</label>
        <select
          className={`${SELECT_CLASS} ${errBorder(errors, "ict_tp_target")}`}
          value={form.ict_tp_target ?? ""}
          onChange={(e) => onChange("ict_tp_target", e.target.value)}
        >
          <option value="">Select target</option>
          {TP_TARGET_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <ErrMsg errors={errors} field="ict_tp_target" />
      </div>

      {/* IFVG Timeframe */}
      <div>
        <label className={LABEL_CLASS}>IFVG Entry Timeframe *</label>
        <select
          className={`${SELECT_CLASS} ${errBorder(errors, "ict_ifvg_timeframe")}`}
          value={form.ict_ifvg_timeframe ?? ""}
          onChange={(e) => onChange("ict_ifvg_timeframe", e.target.value)}
        >
          <option value="">Select TF</option>
          {IFVG_TF_OPTIONS.map((tf) => (
            <option key={tf} value={tf}>{tf.toUpperCase()}</option>
          ))}
        </select>
        <ErrMsg errors={errors} field="ict_ifvg_timeframe" />
      </div>

      {/* SMT + TDO — side by side */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={LABEL_CLASS}>SMT Present *</label>
          <select
            className={`${SELECT_CLASS} ${errBorder(errors, "ict_smt_present")}`}
            value={form.ict_smt_present === null || form.ict_smt_present === undefined ? "" : String(form.ict_smt_present)}
            onChange={(e) => onChange("ict_smt_present", e.target.value === "" ? null : e.target.value === "true")}
          >
            <option value="">Select</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
          <ErrMsg errors={errors} field="ict_smt_present" />
        </div>
        <div>
          <label className={LABEL_CLASS}>TDO Aligned *</label>
          <select
            className={`${SELECT_CLASS} ${errBorder(errors, "ict_tdo_aligned")}`}
            value={form.ict_tdo_aligned === null || form.ict_tdo_aligned === undefined ? "" : String(form.ict_tdo_aligned)}
            onChange={(e) => onChange("ict_tdo_aligned", e.target.value === "" ? null : e.target.value === "true")}
          >
            <option value="">Select</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
          <ErrMsg errors={errors} field="ict_tdo_aligned" />
        </div>
      </div>
    </div>
  );
}
