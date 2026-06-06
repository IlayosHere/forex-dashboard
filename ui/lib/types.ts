export type InstrumentType = "forex" | "futures" | "futures_mnq" | "futures_mes";
export type BeOutcome = "prevented_loss" | "missed_tp";
export type TradingFeeling =
  | "calm" | "focused" | "confident"
  | "anxious" | "impatient" | "fearful" | "greedy" | "distracted" | "revenge" | "tired";

// ICT trade params — MNQ only
export type IctSetupType = "liquidity_sweep" | "unmitigated_fvg" | "continuation" | "other";
export type IctLiquiditySweepDetail =
  | "london_high" | "london_low" | "asia_high" | "asia_low"
  | "data_high" | "data_low"
  | "1m_high" | "1m_low" | "5m_high" | "5m_low"
  | "15m_high" | "15m_low" | "1h_high" | "1h_low"
  | "4h_high" | "4h_low" | "other";
export type IctUnmitigatedFvgDetail = "15m" | "30m" | "1h" | "2h" | "4h" | "other";
export type IctContinuationDetail = "3m" | "5m" | "15m" | "other";
export type IctSetupDetail = IctLiquiditySweepDetail | IctUnmitigatedFvgDetail | IctContinuationDetail;
export type IctTpTarget =
  | "london_high" | "london_low" | "asia_high" | "asia_low"
  | "data_high" | "data_low"
  | "1m_high" | "1m_low" | "5m_high" | "5m_low" | "15m_high" | "15m_low"
  | "1h_high" | "1h_low" | "4h_high" | "4h_low" | "1d_high" | "1d_low"
  | "unmitigated_5m_fvg" | "unmitigated_15m_fvg" | "unmitigated_30m_fvg" | "unmitigated_1h_fvg" | "unmitigated_4h_fvg"
  | "ath"
  | "other";
export type IctIfvgTimeframe = "1m" | "2m" | "3m" | "4m" | "5m" | "6m" | "7m" | "8m" | "9m" | "10m" | "15m" | "other";

// QT trade params — qt-mnq strategy only
export type QtQuarter =
  | "asia_q1" | "asia_q2" | "asia_q3" | "asia_q4"
  | "london_q1" | "london_q2" | "london_q3" | "london_q4"
  | "ny_am_q1" | "ny_am_q2" | "ny_am_q3" | "ny_am_q4"
  | "ny_pm_q1" | "ny_pm_q2" | "ny_pm_q3" | "ny_pm_q4";

export type QtFvgType = "standard" | "inverse";
export type QtEntryType = "limit_fvg_edge" | "market_mss";

export type AccountType = "demo" | "live" | "funded" | "backtest";
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
  ict_ifvg_bars?: number | null;
  ict_smt_present?: boolean | null;
  ict_tdo_aligned?: boolean | null;
  ict_htf_bias?: string | null;
  fees?: number | null;
  criteria_met_at_entry?: boolean | null;
  feeling_before?: TradingFeeling | null;
  feeling_during?: TradingFeeling | null;
  feeling_after?: TradingFeeling | null;
  be_outcome?: BeOutcome | null;
  qt_fvg_quarter?: string | null;
  qt_entry_quarter?: string | null;
  qt_fvg_date?: string | null;
  qt_fvg_type?: string | null;
  qt_entry_type?: string | null;
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
  ict_ifvg_bars?: number | null;
  ict_smt_present?: boolean | null;
  ict_tdo_aligned?: boolean | null;
  ict_htf_bias?: string | null;
  fees?: number | null;
  rule_followed?: boolean | null;
  criteria_met_at_entry?: boolean | null;
  feeling_before?: TradingFeeling | null;
  feeling_during?: TradingFeeling | null;
  feeling_after?: TradingFeeling | null;
  be_outcome?: BeOutcome | null;
  qt_fvg_quarter?: string | null;
  qt_entry_quarter?: string | null;
  qt_fvg_date?: string | null;
  qt_fvg_type?: string | null;
  qt_entry_type?: string | null;
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
  ict_ifvg_bars: number | null;
  ict_smt_present: boolean | null;
  ict_tdo_aligned: boolean | null;
  ict_htf_bias: string | null;
  fees: number | null;
  rule_followed: boolean | null;
  criteria_met_at_entry: boolean | null;
  feeling_before: TradingFeeling | null;
  feeling_during: TradingFeeling | null;
  feeling_after: TradingFeeling | null;
  be_outcome: BeOutcome | null;
  qt_fvg_quarter: QtQuarter | null;
  qt_entry_quarter: QtQuarter | null;
  qt_fvg_date: string | null;
  qt_fvg_type: QtFvgType | null;
  qt_entry_type: QtEntryType | null;
  linked_mistakes: LinkedMistake[];
  created_at: string;
  updated_at: string;
}

export interface TradingSession {
  id: string;
  owner: string;
  date: string;
  had_pre_session_plan: boolean | null;
  feeling_pre: TradingFeeling | null;
  feeling_during: TradingFeeling | null;
  feeling_post: TradingFeeling | null;
  session_notes: string;
  created_at: string;
  updated_at: string;
}

export interface SessionUpsertRequest {
  had_pre_session_plan: boolean | null;
  feeling_pre: TradingFeeling | null;
  feeling_during: TradingFeeling | null;
  feeling_post: TradingFeeling | null;
  session_notes: string;
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
  total_r?: number;
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

export interface ComplianceBucket {
  total: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  total_pnl_usd: number;
  avg_rr: number | null;
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
  total_r?: number;
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
    total_r?: number;
  }>;
  by_day_of_week: Record<string, BreakdownEntry>;
  by_session: Record<string, BreakdownEntry>;
  by_confidence: Record<string, BreakdownEntry>;
  by_rating: Record<string, BreakdownEntry>;
  by_rule_compliance?: Record<string, ComplianceBucket>;
  by_criteria_met?: Record<string, ComplianceBucket>;
  be_outcome_breakdown?: { prevented_loss: number; missed_tp: number; unreviewed: number };
  r_distribution?: RDistributionBin[];
  drawdown?: DrawdownStats | null;
  robustness?: RobustnessStats | null;
  expectancy_ci?: ExpectancyCi | null;
  live_drawdown?: {
    max_drawdown_usd: number
    max_drawdown_r: number
    current_drawdown_usd: number
    current_drawdown_pct: number
    drawdown_trade_count: number
    recovery_factor: number | null
  } | null
  avg_tp_capture_pct?: number | null
  tp_capture_sample_size?: number
}

export interface RDistributionBin {
  bucket_label: string;
  count: number;
  pct: number;
}

export interface DrawdownStats {
  max_drawdown_r: number;
  max_losing_streak: number;
  expected_max_streak: number | null;
  recovery_factor: number | null;
}

export interface RobustnessStats {
  profit_factor_ex_outliers: number | null;
  largest_trade_pct_of_pnl: number | null;
}

export interface ExpectancyCi {
  expectancy_r: number | null;
  expectancy_r_ci_low: number | null;
  expectancy_r_ci_high: number | null;
  edge_significant: boolean | null;
}

export interface RollingPfPoint {
  index: number;
  profit_factor: number | null;
}

export interface RollingExpectancyPoint {
  index: number;
  close_time: string;
  rolling_expectancy_r: number;
}

export interface EquityCurvePoint {
  date: string | null;
  close_time: string | null;
  pnl_usd: number;
  pnl_pips: number;
  cumulative_pnl_usd: number;
  cumulative_pnl_pips: number;
  pnl_r: number;
  cumulative_r: number;
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
  pnl_r: number;
  compliant: number;
  mistakes: number;
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

/** Alias used by the compliance API responses — same shape as Mistake. */
export type MistakeResponse = Mistake;

export interface LinkedMistake {
  id: string;
  name: string;
}

// ---------------------------------------------------------------------------
// Rules
// ---------------------------------------------------------------------------

export interface RuleCategory {
  id: string;
  name: string;
  created_at: string;
}

export interface Rule {
  id: string;
  title: string;
  body: string | null;
  break_count: number;
  created_at: string;
  updated_at: string;
  category: RuleCategory | null;
  linked_mistakes: LinkedMistake[];
}

