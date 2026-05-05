"use client";

import type { Trade } from "@/lib/types";

export interface IctParamsState {
  ict_setup_type: string;
  ict_setup_detail: string;
  ict_tp_target: string;
  ict_ifvg_timeframe: string;
  ict_ifvg_bars: string;
  ict_smt_present: string;
  ict_tdo_aligned: string;
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
    ict_htf_bias: trade.ict_htf_bias ?? "",
  };
}

interface IctParamsPanelProps {
  params: IctParamsState;
  onChange: <K extends keyof IctParamsState>(key: K, value: string) => void;
}

const SELECT_CLASS =
  "bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull w-full h-8 cursor-pointer transition-colors";

const LABEL_CLASS = "block text-xs text-text-muted mb-1";

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
        <select className={SELECT_CLASS} value={params.ict_setup_type} onChange={(e) => handleSetupTypeChange(e.target.value)}>
          <option value="">Select setup type</option>
          <option value="liquidity_sweep">Liquidity Sweep</option>
          <option value="unmitigated_fvg">Unmitigated FVG</option>
          <option value="continuation">Continuation</option>
          <option value="other">Other</option>
        </select>
      </div>

      {params.ict_setup_type && (
        <div>
          <label className={LABEL_CLASS}>{setupDetailLabel}</label>
          <select className={SELECT_CLASS} value={params.ict_setup_detail} onChange={(e) => onChange("ict_setup_detail", e.target.value)}>
            <option value="">Select...</option>
            {setupDetailOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      )}

      <div>
        <label className={LABEL_CLASS}>TP Target</label>
        <select className={SELECT_CLASS} value={params.ict_tp_target} onChange={(e) => onChange("ict_tp_target", e.target.value)}>
          <option value="">Select target</option>
          {TP_TARGET_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={LABEL_CLASS}>IFVG Entry Timeframe</label>
          <select className={SELECT_CLASS} value={params.ict_ifvg_timeframe} onChange={(e) => onChange("ict_ifvg_timeframe", e.target.value)}>
            <option value="">Select TF</option>
            {IFVG_TF_OPTIONS.map((tf) => (
              <option key={tf} value={tf}>{tf.toUpperCase()}</option>
            ))}
          </select>
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
        <select className={SELECT_CLASS} value={params.ict_htf_bias} onChange={(e) => onChange("ict_htf_bias", e.target.value)}>
          <option value="">Select bias</option>
          {HTF_BIAS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={LABEL_CLASS}>SMT Present</label>
          <select className={SELECT_CLASS} value={params.ict_smt_present} onChange={(e) => onChange("ict_smt_present", e.target.value)}>
            <option value="">Select</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>
        <div>
          <label className={LABEL_CLASS}>TDO Aligned</label>
          <select className={SELECT_CLASS} value={params.ict_tdo_aligned} onChange={(e) => onChange("ict_tdo_aligned", e.target.value)}>
            <option value="">Select</option>
            <option value="true">Yes</option>
            <option value="false">No</option>
          </select>
        </div>
      </div>

    </div>
  );
}
