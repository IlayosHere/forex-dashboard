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
  by_entry_model: Record<string, IctBucketStats>;
  by_pd_array: Record<string, IctBucketStats>;
  by_killzone: Record<string, IctBucketStats>;
  boolean_flags: Record<string, IctBooleanComparison>;
  combo_matrix: IctComboEntry[];
}
