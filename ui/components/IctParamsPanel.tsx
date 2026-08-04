"use client";

import { Combobox } from "@/components/ui/combobox";

import { IFVG_TIMEFRAMES } from "@/lib/ictConstants";
import type { Trade } from "@/lib/types";

export interface IctParamsState {
  ict_setup_type: string;
  ict_setup_detail: string;
  ict_tp_target: string;
  ict_ifvg_timeframe: string;
  ict_ifvg_bars: string;
  ict_smt_present: string;
  ict_tdo_aligned: string;
  ict_cisd_present: string;
  ict_htf_bias: string;
}

export function ictParamsFromTrade(trade: Trade): IctParamsState {
  return {
    ict_setup_type: trade.ict_setup_type ?? "",
    ict_setup_detail: trade.ict_setup_detail ?? "",
    ict_tp_target: trade.ict_tp_target ?? "",
    ict_ifvg_timeframe: trade.ict_ifvg_timeframe ?? "",
    ict_ifvg_bars: trade.ict_ifvg_bars != null ? String(trade.ict_ifvg_bars) : "",
    ict_smt_present: trade.ict_smt_present === null ? "" : String(trade.ict_smt_present),
    ict_tdo_aligned: trade.ict_tdo_aligned === null ? "" : String(trade.ict_tdo_aligned),
    ict_cisd_present: trade.ict_cisd_present === null ? "" : String(trade.ict_cisd_present),
    ict_htf_bias: trade.ict_htf_bias ?? "",
  };
}

interface IctParamsPanelProps {
  params: IctParamsState;
  onChange: <K extends keyof IctParamsState>(key: K, value: string) => void;
}

const LABEL_CLASS = "block text-xs text-text-muted mb-1";

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

const HTF_BIAS_OPTIONS = [
  { value: "aligned", label: "Aligned" },
  { value: "counter", label: "Counter" },
  { value: "neutral", label: "Neutral" },
];

export function IctParamsPanel({ params, onChange }: IctParamsPanelProps) {
  const setupDetailOptions = params.ict_setup_type
    ? SETUP_DETAIL_OPTIONS[params.ict_setup_type] ?? []
    : [];
  const setupDetailLabel = params.ict_setup_type
    ? SETUP_DETAIL_LABEL[params.ict_setup_type] ?? "Setup Detail"
    : "Setup Detail";

  const handleSetupTypeChange = (value: string) => {
    onChange("ict_setup_type", value);
    onChange("ict_setup_detail", "");
  };

  return (
    <div className="border border-border rounded-lg p-4 bg-card space-y-4">
      <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">ICT Setup</p>

      <div>
        <label className={LABEL_CLASS}>Setup Type</label>
        <Combobox
          options={SETUP_TYPE_OPTIONS}
          value={params.ict_setup_type || null}
          onChange={(v) => handleSetupTypeChange(v ?? "")}
          placeholder="Select setup type"
          filterable={false}
        />
      </div>

      {params.ict_setup_type && (
        <div>
          <label className={LABEL_CLASS}>{setupDetailLabel}</label>
          <Combobox
            options={setupDetailOptions}
            value={params.ict_setup_detail || null}
            onChange={(v) => onChange("ict_setup_detail", v ?? "")}
          />
        </div>
      )}

      <div>
        <label className={LABEL_CLASS}>TP Target</label>
        <Combobox
          options={TP_TARGET_OPTIONS}
          value={params.ict_tp_target || null}
          onChange={(v) => onChange("ict_tp_target", v ?? "")}
          placeholder="Select target"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={LABEL_CLASS}>IFVG Entry Timeframe</label>
          <Combobox
            options={IFVG_TIMEFRAMES.map((tf) => ({ value: tf, label: tf.toUpperCase() }))}
            value={params.ict_ifvg_timeframe || null}
            onChange={(v) => onChange("ict_ifvg_timeframe", v ?? "")}
            placeholder="Select TF"
          />
        </div>
        <div>
          <label className={LABEL_CLASS}>Bars to IFVG</label>
          <input
            type="number"
            min={1}
            max={100}
            placeholder="e.g. 2"
            className="bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull w-full h-8 transition-colors [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
            value={params.ict_ifvg_bars}
            onChange={(e) => onChange("ict_ifvg_bars", e.target.value)}
          />
        </div>
      </div>

      <div>
        <label className={LABEL_CLASS}>HTF Bias</label>
        <Combobox
          options={HTF_BIAS_OPTIONS}
          value={params.ict_htf_bias || null}
          onChange={(v) => onChange("ict_htf_bias", v ?? "")}
          placeholder="Select bias"
          filterable={false}
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={LABEL_CLASS}>SMT Present</label>
          <Combobox
            options={YES_NO_OPTIONS}
            value={params.ict_smt_present || null}
            onChange={(v) => onChange("ict_smt_present", v ?? "")}
            placeholder="Select"
            filterable={false}
          />
        </div>
        <div>
          <label className={LABEL_CLASS}>TDO Aligned</label>
          <Combobox
            options={YES_NO_OPTIONS}
            value={params.ict_tdo_aligned || null}
            onChange={(v) => onChange("ict_tdo_aligned", v ?? "")}
            placeholder="Select"
            filterable={false}
          />
        </div>
        <div>
          <label className={LABEL_CLASS}>CISD Present</label>
          <Combobox
            options={YES_NO_OPTIONS}
            value={params.ict_cisd_present || null}
            onChange={(v) => onChange("ict_cisd_present", v ?? "")}
            placeholder="Select"
            filterable={false}
          />
        </div>
      </div>

    </div>
  );
}
