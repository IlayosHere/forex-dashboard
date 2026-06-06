"use client";

import type { RobustnessStats, ExpectancyCi } from "@/lib/types";

import { fmt } from "@/lib/format";
import { COLOR_BULL, COLOR_BEAR, SMALL_SAMPLE_THRESHOLD } from "@/lib/statsHelpers";

interface RobustnessPanelProps {
  robustness: RobustnessStats | null | undefined;
  expectancy_ci: ExpectancyCi | null | undefined;
  sampleSize: number;
}

interface MetricRowProps {
  label: string;
  value: string;
  color?: string;
  sub?: string;
  dimmed?: boolean;
}

const COLOR_AMBER = "#f59e0b";

function MetricRow({ label, value, color, sub, dimmed }: MetricRowProps) {
  return (
    <div className={`flex justify-between items-start py-1.5 ${dimmed ? "opacity-40" : ""}`}>
      <span className="text-xs text-text-muted">{label}</span>
      <span className="text-right">
        <span
          className="text-sm font-semibold price block tabular-nums"
          style={{ color: color ?? "#e0e0e0" }}
        >
          {value}
        </span>
        {sub && <span className="text-[10px] text-text-muted">{sub}</span>}
      </span>
    </div>
  );
}

function expectancyLabel(ci: ExpectancyCi): string {
  const r = ci.expectancy_r;
  const lo = ci.expectancy_r_ci_low;
  const hi = ci.expectancy_r_ci_high;
  if (r == null) return "—";
  if (lo != null && hi != null) {
    return `${fmt(r, 2)}R [${fmt(lo, 2)}, ${fmt(hi, 2)}]`;
  }
  return `${fmt(r, 2)}R`;
}

function expectancyColor(ci: ExpectancyCi | null | undefined): string {
  if (ci?.edge_significant === true) return COLOR_BULL;
  return "#777777";
}

function largestTradePctColor(pct: number | null): string {
  if (pct == null) return "#e0e0e0";
  return pct > 25 ? COLOR_AMBER : "#e0e0e0";
}

export function RobustnessPanel({ robustness, expectancy_ci, sampleSize }: RobustnessPanelProps) {
  const lowSample = sampleSize < SMALL_SAMPLE_THRESHOLD;
  const ci = expectancy_ci;

  const pfExOutliers = robustness?.profit_factor_ex_outliers ?? null;
  const largestPct = robustness?.largest_trade_pct_of_pnl ?? null;

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-xs uppercase tracking-wide text-text-muted mb-3">Robustness</h3>
      <div className="divide-y divide-border">
        <div className={`flex justify-between items-start py-1.5 ${lowSample ? "opacity-40" : ""}`}>
          <span className="text-xs text-text-muted">Avg R ± CI</span>
          <span className="text-right">
            <span
              className="text-sm font-semibold price block tabular-nums"
              style={{ color: expectancyColor(ci) }}
            >
              {lowSample
                ? "—"
                : ci != null
                  ? expectancyLabel(ci)
                  : "—"}
            </span>
            {lowSample && (
              <span className="text-[10px] text-text-muted">
                Need {SMALL_SAMPLE_THRESHOLD - sampleSize} more trades
              </span>
            )}
            {!lowSample && ci?.edge_significant === false && (
              <span className="text-[10px] text-text-muted">edge not significant</span>
            )}
          </span>
        </div>
        <MetricRow
          label="PF ex-outliers"
          value={pfExOutliers != null ? fmt(pfExOutliers, 2) : "—"}
          color={pfExOutliers != null ? (pfExOutliers >= 1.5 ? COLOR_BULL : pfExOutliers >= 1 ? COLOR_AMBER : COLOR_BEAR) : undefined}
        />
        <MetricRow
          label="Largest Trade % of P&L"
          value={largestPct != null ? `${fmt(largestPct, 1)}%` : "—"}
          color={largestTradePctColor(largestPct)}
          sub={largestPct != null && largestPct > 25 ? "concentrated risk" : undefined}
        />
      </div>
    </div>
  );
}
