export type InstrumentType = "forex" | "futures_mnq";
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
  close_time?: string | null;
  tags?: string[] | null;
  notes?: string | null;
  rating?: number | null;
  confidence?: number | null;
  screenshot_url?: string | null;
  metadata?: Record<string, unknown> | null;
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

export interface AnalyticsCorrelation {
  param_name: string;
  correlation: number;
  p_value: number;
  significant: boolean;
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
}

export interface AnalyticsParameter {
  name: string;
  dtype: "float" | "str" | "int" | "bool";
  strategies: string[];
  needs_candles: boolean;
}

export interface AnalyticsParameterList {
  items: AnalyticsParameter[];
  total: number;
}
