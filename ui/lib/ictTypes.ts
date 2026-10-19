export interface IctBucketStats {
  total: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  total_pnl_usd: number;
  avg_pnl_usd: number | null;
  avg_rr: number | null;
  expectancy_r: number | null;
}

export interface IctBooleanComparison {
  true: IctBucketStats;
  false: IctBucketStats;
}

export interface IctComboEntry {
  setup_type: string;
  mnq_session: string | null;
  htf_bias: string | null;
  total: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  total_pnl_usd: number;
  avg_rr: number | null;
  expectancy_r: number | null;
}

export interface IctIfvgBarsRow {
  bars_label: string;    // "1", "2", ..., "10", "10+"
  timeframe: string;     // "1m", "3m", etc.
  total: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  total_pnl_usd: number;
  avg_pnl_usd: number | null;
  avg_rr: number | null;
  expectancy_r: number | null;
}

export interface IctStatsResponse {
  total_trades: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  by_setup_type: Record<string, IctBucketStats>;
  by_tp_target: Record<string, IctBucketStats>;
  by_ifvg_timeframe: Record<string, IctBucketStats>;
  by_mnq_session: Record<string, IctBucketStats>;
  by_htf_bias: Record<string, IctBucketStats>;
  by_killzone: Record<string, IctBucketStats>;
  boolean_flags: Record<string, IctBooleanComparison>;
  combo_matrix: IctComboEntry[];
  ifvg_bars_matrix: IctIfvgBarsRow[];
  time_edge?: TimeEdgeStats | null;
}

export interface TimeMatrixCell {
  row: string;
  phase: string;
  stats: IctBucketStats;
}

export interface TimeInsight {
  kind: "strength" | "weakness";
  dimension: string;
  row: string;
  phase: string;
  stats: IctBucketStats;
}

export interface TimeEdgeStats {
  by_ny_phase: Record<string, IctBucketStats>;
  by_time_slice: Record<string, IctBucketStats>;
  by_macro: Record<string, IctBucketStats>;
  matrices: Record<string, TimeMatrixCell[]>;
  insights: TimeInsight[];
  min_sample: number;
}
