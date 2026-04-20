export interface IctBucketStats {
  total: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  total_pnl_usd: number;
  avg_pnl_usd: number | null;
  avg_rr: number | null;
}

export interface IctBooleanComparison {
  true: IctBucketStats;
  false: IctBucketStats;
}

export interface IctComboEntry {
  setup_type: string;
  smt_present: boolean | null;
  tdo_aligned: boolean | null;
  total: number;
  wins: number;
  losses: number;
  win_rate: number | null;
  total_pnl_usd: number;
  avg_rr: number | null;
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
  boolean_flags: Record<string, IctBooleanComparison>;
  combo_matrix: IctComboEntry[];
}
