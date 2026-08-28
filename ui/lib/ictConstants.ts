import type { IctIfvgTimeframe } from "./types";

// Mirrors shared/ict_taxonomy.py::IFVG_TIMEFRAMES — the backend validator
// rejects any ict_ifvg_timeframe value not in this list.
export const IFVG_TIMEFRAMES: IctIfvgTimeframe[] = ["30s", "1m", "2m", "3m", "4m", "5m"];

export interface IctOption {
  value: string;
  label: string;
}

// Mirrors shared/ict_taxonomy.py::SETUP_DETAIL_MAP — entry-side "why I got in" detail,
// keyed by ict_setup_type. Shared by IctTradeFields (create) and IctParamsPanel (edit)
// so both forms always offer the same choices.
export const SETUP_DETAIL_OPTIONS: Record<string, IctOption[]> = {
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
    { value: "1D", label: "1D FVG" },
    { value: "1W", label: "1W FVG" },
    { value: "1M", label: "1M FVG" },
    { value: "other", label: "Other" },
  ],
  continuation: [
    { value: "3m", label: "3M FVG" },
    { value: "5m", label: "5M FVG" },
    { value: "15m", label: "15M FVG" },
    { value: "other", label: "Other" },
  ],
};

export const SETUP_DETAIL_LABEL: Record<string, string> = {
  liquidity_sweep: "Liquidity Level Swept",
  unmitigated_fvg: "FVG Timeframe",
  continuation: "Continuation FVG Timeframe",
};

// Mirrors shared/ict_taxonomy.py::TP_TARGETS — real ICT draw-on-liquidity concepts only.
// No raw low-timeframe candle highs/lows; those live under ith/itl + a timeframe detail.
export const TP_TARGET_OPTIONS: IctOption[] = [
  { value: "asia_high", label: "Asia High" },
  { value: "asia_low", label: "Asia Low" },
  { value: "london_high", label: "London High" },
  { value: "london_low", label: "London Low" },
  { value: "prev_session_high", label: "Prev Session High" },
  { value: "prev_session_low", label: "Prev Session Low" },
  { value: "pdh", label: "PDH (Prev Day High)" },
  { value: "pdl", label: "PDL (Prev Day Low)" },
  { value: "pwh", label: "PWH (Prev Week High)" },
  { value: "pwl", label: "PWL (Prev Week Low)" },
  { value: "pmh", label: "PMH (Prev Month High)" },
  { value: "pml", label: "PML (Prev Month Low)" },
  { value: "ith", label: "ITH (Swing High)" },
  { value: "itl", label: "ITL (Swing Low)" },
  { value: "nwog", label: "NWOG (New Week Opening Gap)" },
  { value: "ndog", label: "NDOG (New Day Opening Gap)" },
  { value: "unmitigated_fvg", label: "Unmitigated FVG" },
  { value: "data_release_high", label: "Data Release High" },
  { value: "data_release_low", label: "Data Release Low" },
  { value: "ath", label: "ATH" },
  { value: "other", label: "Other" },
];

// Mirrors shared/ict_taxonomy.py::TP_TARGET_DETAIL_MAP — sub-selection shown only when
// ict_tp_target is one of these keys. Any other tp_target takes no detail.
export const TP_TARGET_DETAIL_OPTIONS: Record<string, IctOption[]> = {
  ith: [
    { value: "5m", label: "5M" },
    { value: "15m", label: "15M" },
    { value: "30m", label: "30M" },
    { value: "1h", label: "1H" },
    { value: "4h", label: "4H" },
    { value: "1D", label: "1D" },
    { value: "1W", label: "1W" },
  ],
  itl: [
    { value: "5m", label: "5M" },
    { value: "15m", label: "15M" },
    { value: "30m", label: "30M" },
    { value: "1h", label: "1H" },
    { value: "4h", label: "4H" },
    { value: "1D", label: "1D" },
    { value: "1W", label: "1W" },
  ],
  unmitigated_fvg: [
    { value: "5m", label: "5M FVG" },
    { value: "15m", label: "15M FVG" },
    { value: "30m", label: "30M FVG" },
    { value: "1h", label: "1H FVG" },
    { value: "2h", label: "2H FVG" },
    { value: "4h", label: "4H FVG" },
    { value: "1D", label: "1D FVG" },
    { value: "1W", label: "1W FVG" },
    { value: "1M", label: "1M FVG" },
  ],
  data_release_high: [
    { value: "cpi", label: "CPI" },
    { value: "ppi", label: "PPI" },
    { value: "nfp", label: "NFP" },
    { value: "fomc", label: "FOMC" },
    { value: "other", label: "Other" },
  ],
  data_release_low: [
    { value: "cpi", label: "CPI" },
    { value: "ppi", label: "PPI" },
    { value: "nfp", label: "NFP" },
    { value: "fomc", label: "FOMC" },
    { value: "other", label: "Other" },
  ],
};

export const TP_TARGET_DETAIL_LABEL: Record<string, string> = {
  ith: "Swing Timeframe",
  itl: "Swing Timeframe",
  unmitigated_fvg: "FVG Timeframe",
  data_release_high: "Release Type",
  data_release_low: "Release Type",
};
