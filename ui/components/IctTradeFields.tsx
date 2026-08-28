"use client";

import { Combobox } from "@/components/ui/combobox";

import { IctExtendedFields } from "./IctExtendedFields";

import type { TradeFormData } from "./TradeForm";

import {
  IFVG_TIMEFRAMES,
  SETUP_DETAIL_LABEL,
  SETUP_DETAIL_OPTIONS,
  TP_TARGET_DETAIL_LABEL,
  TP_TARGET_DETAIL_OPTIONS,
  TP_TARGET_OPTIONS,
} from "@/lib/ictConstants";

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

  const tpTargetDetailOptions = form.ict_tp_target ? TP_TARGET_DETAIL_OPTIONS[form.ict_tp_target] ?? [] : [];
  const tpTargetDetailLabel = form.ict_tp_target
    ? TP_TARGET_DETAIL_LABEL[form.ict_tp_target] ?? "Target Detail"
    : "Target Detail";

  const handleTpTargetChange = (value: string) => {
    onChange("ict_tp_target", value);
    onChange("ict_tp_target_detail", ""); // reset detail when target changes
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
          onChange={(v) => handleTpTargetChange(v ?? "")}
          placeholder="Select target"
        />
        <ErrMsg errors={errors} field="ict_tp_target" />
      </div>

      {/* TP Target Detail — context-sensitive, only for targets that take one */}
      {tpTargetDetailOptions.length > 0 && (
        <div>
          <label className={LABEL_CLASS}>{tpTargetDetailLabel} *</label>
          <Combobox
            className={errBorder(errors, "ict_tp_target_detail")}
            options={tpTargetDetailOptions}
            value={form.ict_tp_target_detail || null}
            onChange={(v) => onChange("ict_tp_target_detail", v ?? "")}
            filterable={false}
          />
          <ErrMsg errors={errors} field="ict_tp_target_detail" />
        </div>
      )}

      {/* IFVG Timeframe + Bars to IFVG — side by side */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={LABEL_CLASS}>IFVG Entry Timeframe *</label>
          <Combobox
            className={errBorder(errors, "ict_ifvg_timeframe")}
            options={IFVG_TIMEFRAMES.map((tf) => ({ value: tf, label: tf.toUpperCase() }))}
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
