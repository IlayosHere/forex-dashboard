"use client";

import type { IctBooleanComparison, IctBucketStats } from "@/lib/ictTypes";

interface IctBooleanFlagsProps {
  booleanFlags: Record<string, IctBooleanComparison> | undefined;
  loading: boolean;
}

const FLAG_LABELS: Record<string, string> = {
  smt_present: "SMT Present",
  tdo_aligned: "TDO Aligned",
  cisd_present: "CISD Present",
};

const FLAG_KEYS = ["smt_present", "tdo_aligned", "cisd_present"] as const;

function formatWinRate(value: number | null): string {
  if (value === null) return "—";
  return `${value.toFixed(0)}%`;
}

function formatPnl(value: number | null): string {
  if (value === null) return "—";
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}$${Math.abs(value).toFixed(0)}`;
}

function winRateColor(value: number | null): string {
  if (value === null) return "text-text-muted";
  return value >= 50 ? "text-bull" : "text-bear";
}

function pnlColor(value: number | null): string {
  if (value === null) return "text-text-muted";
  return value >= 0 ? "text-bull" : "text-bear";
}

interface MetricRowProps {
  label: string;
  withBucket: IctBucketStats;
  withoutBucket: IctBucketStats;
}

function WinRateRow({ label, withBucket, withoutBucket }: MetricRowProps) {
  return (
    <div className="grid grid-cols-3 gap-2 py-1">
      <span className="text-xs text-text-muted">{label}</span>
      <span className={`text-sm font-medium tabular-nums ${winRateColor(withBucket.win_rate)}`}>
        {formatWinRate(withBucket.win_rate)}
      </span>
      <span className={`text-sm font-medium tabular-nums ${winRateColor(withoutBucket.win_rate)}`}>
        {formatWinRate(withoutBucket.win_rate)}
      </span>
    </div>
  );
}

function PnlRow({ label, withBucket, withoutBucket }: MetricRowProps) {
  return (
    <div className="grid grid-cols-3 gap-2 py-1">
      <span className="text-xs text-text-muted">{label}</span>
      <span className={`text-sm font-medium tabular-nums ${pnlColor(withBucket.avg_pnl_usd)}`}>
        {formatPnl(withBucket.avg_pnl_usd)}
      </span>
      <span className={`text-sm font-medium tabular-nums ${pnlColor(withoutBucket.avg_pnl_usd)}`}>
        {formatPnl(withoutBucket.avg_pnl_usd)}
      </span>
    </div>
  );
}

function TradesRow({ withBucket, withoutBucket }: { withBucket: IctBucketStats; withoutBucket: IctBucketStats }) {
  return (
    <div className="grid grid-cols-3 gap-2 py-1">
      <span className="text-xs text-text-muted">Trades</span>
      <span className="text-sm font-medium tabular-nums text-text-primary">{withBucket.total}</span>
      <span className="text-sm font-medium tabular-nums text-text-primary">{withoutBucket.total}</span>
    </div>
  );
}

interface FlagCardProps {
  flagKey: string;
  comparison: IctBooleanComparison;
}

function FlagCard({ flagKey, comparison }: FlagCardProps) {
  const withBucket = comparison.true;
  const withoutBucket = comparison.false;
  const impact = withBucket.win_rate !== null && withoutBucket.win_rate !== null
    ? withBucket.win_rate - withoutBucket.win_rate
    : null;
  const impactColor = impact === null ? "text-text-muted" : impact > 0 ? "text-bull" : "text-bear";
  const impactStr = impact === null
    ? "—"
    : `${impact > 0 ? "+" : ""}${impact.toFixed(0)}pp`;

  return (
    <div className="bg-card border border-border rounded-lg p-4 flex-1">
      <p className="text-xs uppercase tracking-widest text-text-muted mb-4">
        {FLAG_LABELS[flagKey] ?? flagKey}
      </p>
      <div className="grid grid-cols-3 gap-2 pb-2 mb-1">
        <span />
        <span className="text-[10px] uppercase text-text-dim font-medium">With</span>
        <span className="text-[10px] uppercase text-text-dim font-medium">Without</span>
      </div>
      <WinRateRow label="Win Rate" withBucket={withBucket} withoutBucket={withoutBucket} />
      <PnlRow label="Avg P&L" withBucket={withBucket} withoutBucket={withoutBucket} />
      <TradesRow withBucket={withBucket} withoutBucket={withoutBucket} />
      <div className={`text-xs font-medium tabular-nums mt-3 pt-3 border-t border-border ${impactColor}`}>
        Edge Impact: {impactStr}
      </div>
    </div>
  );
}

export function IctBooleanFlags({ booleanFlags, loading }: IctBooleanFlagsProps) {
  const dim = loading ? "opacity-50" : "";
  const hasData = booleanFlags && Object.keys(booleanFlags).length > 0;

  if (!hasData) {
    return (
      <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
        <p className="text-text-muted text-sm text-center py-4">No MNQ trades to analyze</p>
      </div>
    );
  }

  return (
    <div className={`flex flex-wrap gap-3 ${dim}`}>
      {FLAG_KEYS.map((key) => {
        const comparison = booleanFlags[key];
        if (!comparison) return null;
        return <FlagCard key={key} flagKey={key} comparison={comparison} />;
      })}
    </div>
  );
}
