export type InstrumentType = "forex" | "futures_mnq";

// ICT trade params — MNQ only
export type IctSetupType = "liquidity_sweep" | "unmitigated_fvg" | "continuation" | "other";
export type IctLiquiditySweepDetail =
  | "london_high" | "london_low" | "asia_high" | "asia_low"
  | "data_high" | "data_low"
  | "1m_high" | "1m_low" | "5m_high" | "5m_low"
  | "15m_high" | "15m_low" | "1h_high" | "1h_low"
  | "4h_high" | "4h_low" | "other";
export type IctUnmitigatedFvgDetail = "15m" | "1h" | "4h" | "other";
export type IctContinuationDetail = "3m" | "5m" | "15m" | "other";
export type IctSetupDetail = IctLiquiditySweepDetail | IctUnmitigatedFvgDetail | IctContinuationDetail;
export type IctTpTarget =
  | "london_high" | "london_low" | "asia_high" | "asia_low"
  | "data_high" | "data_low"
  | "1m_high" | "1m_low" | "5m_high" | "5m_low" | "15m_high" | "15m_low"
  | "unmitigated_5m_fvg" | "unmitigated_15m_fvg" | "unmitigated_1h_fvg" | "unmitigated_4h_fvg"
  | "other";
export type IctIfvgTimeframe = "1m" | "2m" | "3m" | "4m" | "5m" | "6m" | "7m" | "8m" | "9m" | "10m" | "15m" | "other";
export type AccountType = "demo" | "live" | "funded";
export type AccountStatus = "active" | "passed" | "failed" | "closed";

export interface Account {
  id: string;
  name: string;
  account_type: AccountType;
  instrument_type: InstrumentType;
  status: AccountStatus;
  prop_firm: string | null;
  phase: string | null;
  balance?: number | null;
  created_at: string;
}

export type SignalResolution = "TP_HIT" | "SL_HIT" | "EXPIRED" | "NOT_FILLED";
export type SlMethod = "far_edge" | "midpoint";

export interface Signal {
  id: string;
  strategy: string;
  symbol: string;
  direction: "BUY" | "SELL";
  candle_time: string;   // ISO datetime string
  entry: number;
  sl: number;
  tp: number;
  lot_size: number;
  risk_pips: number;
  spread_pips: number;
  metadata: Record<string, unknown>;
  created_at: string;    // ISO datetime string
  // Resolution — populated by runner/resolver.py after signal plays out
  resolution: SignalResolution | null;
  resolved_at: string | null;
  resolved_price: number | null;
  resolution_candles: number | null;
}

export interface SignalListResponse {
  items: Signal[];
  total: number;
}

export interface CalculateResponse {
  lot_size: number;
  risk_usd: number;
  sl_pips: number;
  rr: number | null;
  instrument_type: string;
}

export interface TradeCreateRequest {
  signal_id?: string | null;
  account_id?: string | null;
  strategy: string;
  symbol: string;
  instrument_type?: string;
  direction: "BUY" | "SELL";
  entry_price: number;
  sl_price: number;
  tp_price?: number | null;
  lot_size: number;
  risk_pips?: number;
  open_time: string;
  tags?: string[];
  notes?: string;
  rating?: number | null;
  confidence?: number | null;
  screenshot_url?: string | null;
  metadata?: Record<string, unknown>;
  ict_setup_type?: string | null;
  ict_setup_detail?: string | null;
  ict_tp_target?: string | null;
  ict_ifvg_timeframe?: string | null;
  ict_smt_present?: boolean | null;
  ict_tdo_aligned?: boolean | null;
  ict_htf_bias?: string | null;
  ict_entry_model?: string | null;
  ict_pd_array?: string | null;
}

export interface TradeUpdateRequest {
  instrument_type?: string | null;
  direction?: "BUY" | "SELL" | null;
  entry_price?: number | null;
  exit_price?: number | null;
  sl_price?: number | null;
  tp_price?: number | null;
  lot_size?: number | null;
  risk_pips?: number | null;
  status?: "open" | "closed" | "breakeven" | "cancelled" | null;
  outcome?: "win" | "loss" | "breakeven" | null;
  open_time?: string | null;
  close_time?: string | null;
  tags?: string[] | null;
  notes?: string | null;
  rating?: number | null;
  confidence?: number | null;
  screenshot_url?: string | null;
  metadata?: Record<string, unknown> | null;
  ict_setup_type?: string | null;
  ict_setup_detail?: string | null;
  ict_tp_target?: string | null;
  ict_ifvg_timeframe?: string | null;
  ict_smt_present?: boolean | null;
  ict_tdo_aligned?: boolean | null;
  ict_htf_bias?: string | null;
  ict_entry_model?: string | null;
  ict_pd_array?: string | null;
}

export interface Trade {
  id: string;
  signal_id: string | null;
  strategy: string;
  symbol: string;
  direction: "BUY" | "SELL";
  entry_price: number;
  exit_price: number | null;
  sl_price: number;
  tp_price: number | null;
  lot_size: number;
  status: "open" | "closed" | "breakeven" | "cancelled";
  outcome: "win" | "loss" | "breakeven" | null;
  pnl_pips: number | null;
  pnl_usd: number | null;
  rr_achieved: number | null;
  risk_pips: number;
  open_time: string;
  close_time: string | null;
  tags: string[];
  notes: string;
  rating: number | null;
  confidence: number | null;
  screenshot_url: string | null;
  instrument_type: InstrumentType | null;
  account_id: string | null;
  account_name: string | null;
  metadata: Record<string, unknown>;
  ict_setup_type: IctSetupType | null;
  ict_setup_detail: IctSetupDetail | null;
  ict_tp_target: IctTpTarget | null;
  ict_ifvg_timeframe: IctIfvgTimeframe | null;
  ict_smt_present: boolean | null;
  ict_tdo_aligned: boolean | null;
  ict_htf_bias: string | null;
  ict_entry_model: string | null;
  ict_pd_array: string | null;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface UserProfile {
  username: string;
  is_admin: boolean;
}

export interface BreakdownEntry {
  total: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  total_pnl_pips: number;
  total_pnl_usd: number;
  avg_pnl_usd: number;
  avg_rr: number | null;
  name: string;
}

// ---------------------------------------------------------------------------
// Economic Calendar
// ---------------------------------------------------------------------------

export type CalendarImpact = "High" | "Medium" | "Low";
export type CalendarContext = "forex" | "mnq";
export type SessionBucket = "pre_market" | "cash_session" | "none";
export type BeatMiss = "beat" | "miss" | "in_line" | "pending";

export interface CalendarEvent {
  id: string;
  name: string;
  currency: string;
  datetime_utc: string;    // ISO 8601 UTC
  datetime_et: string;     // ISO 8601 ET (pre-computed by backend)
  impact: CalendarImpact;
  promoted: boolean;       // true = officially Medium but practically High
  previous: string | null;
  forecast: string | null;
  actual: string | null;   // null until released
  beat_miss: BeatMiss;     // computed by backend from actual vs forecast
  session_bucket: SessionBucket; // pre_market / cash_session / none
}

export interface TradeStats {
  total_trades: number;
  open_trades: number;
  closed_trades: number;
  wins: number;
  losses: number;
  breakevens: number;
  win_rate: number | null;
  avg_rr: number | null;
  total_pnl_pips: number;
  total_pnl_usd: number;
  best_trade_pnl: number | null;
  worst_trade_pnl: number | null;
  current_streak: number;
  profit_factor: number | null;
  avg_hold_time_hours: number | null;
  avg_win_pips: number | null;
  avg_loss_pips: number | null;
  avg_win_usd: number | null;
  avg_loss_usd: number | null;
  expectancy_usd: number | null;
  expectancy_pips: number | null;
  consistency_ratio: number | null;
  by_strategy: Record<string, { total: number; wins: number; losses: number; win_rate: number | null; total_pnl_pips: number; total_pnl_usd: number; avg_pnl_usd: number; avg_rr: number | null }>;
  by_symbol: Record<string, { total: number; wins: number; losses: number; win_rate: number | null; total_pnl_pips: number; total_pnl_usd: number; avg_pnl_usd: number; avg_rr: number | null }>;
  by_account: Record<string, {
    account_name: string;
    account_type: AccountType;
    instrument_type: InstrumentType;
    total: number;
    wins: number;
    losses: number;
    win_rate: number | null;
    total_pnl_pips: number;
    total_pnl_usd: number;
  }>;
  by_day_of_week: Record<string, BreakdownEntry>;
  by_session: Record<string, BreakdownEntry>;
  by_confidence: Record<string, BreakdownEntry>;
  by_rating: Record<string, BreakdownEntry>;
}

export interface EquityCurvePoint {
  date: string | null;
  close_time: string | null;
  pnl_usd: number;
  pnl_pips: number;
  cumulative_pnl_usd: number;
  cumulative_pnl_pips: number;
  trade_count: number;
  outcome: string | null;
}

export interface DailySummaryPoint {
  date: string;
  trades: number;
  wins: number;
  losses: number;
  breakevens: number;
  pnl_usd: number;
  pnl_pips: number;
}

// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

export type { AnalyticsLevel } from "./analyticsLevels";

import type { AnalyticsLevel } from "./analyticsLevels";

export interface AnalyticsCorrelation {
  param_name: string;
  correlation: number | null;
  p_value: number | null;
  significant: boolean;
  delta: number | null;
  ci_lo: number | null;
  ci_hi: number | null;
  best_bucket: string | null;
  level: AnalyticsLevel | null;
  fdr_status: "confirmed" | "exploratory" | "insufficient_data";
}

export interface AnalyticsSummary {
  strategy: string;
  total_resolved: number;
  win_rate_overall: number;
  params_analyzed: number;
  top_correlations: AnalyticsCorrelation[];
}

export interface AnalyticsBucket {
  bucket_label: string;
  wins: number;
  losses: number;
  total: number;
  win_rate: number;
  ci_lower: number;
  ci_upper: number;
}

export interface UnivariateReport {
  param_name: string;
  dtype: "categorical" | "numeric";
  strategy: string;
  total_signals: number;
  buckets: AnalyticsBucket[];
  chi_squared: number | null;
  chi_p_value: number | null;
  correlation: number | null;
  correlation_p_value: number | null;
  delta: number | null;
  ci_lo: number | null;
  ci_hi: number | null;
  best_bucket: string | null;
  level: AnalyticsLevel | null;
}

// ---------------------------------------------------------------------------
// Regime Detection
// ---------------------------------------------------------------------------

export interface RegimeWindowStats {
  n: number;
  win_rate: number;
  wins: number;
}

export type RegimeStatus = "healthy" | "warning" | "degraded" | "insufficient_data";

export interface RegimeResult {
  strategy: string;
  symbol: string | null;
  recent: RegimeWindowStats;
  prior: RegimeWindowStats;
  delta: number;
  z_score: number | null;
  status: RegimeStatus;
  sufficient_data: boolean;
}

// ---------------------------------------------------------------------------
// Mistakes Tracker
// ---------------------------------------------------------------------------

export interface Mistake {
  id: string;
  name: string;
  count: number;
  last_occurred_at: string;
  created_at: string;
}

