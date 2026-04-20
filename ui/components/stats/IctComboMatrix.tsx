"use client";

import { useState, useMemo } from "react";

import type { IctComboEntry } from "@/lib/ictTypes";

interface IctComboMatrixProps {
  comboMatrix: IctComboEntry[];
  loading: boolean;
}

const SETUP_TYPE_LABELS: Record<string, string> = {
  liquidity_sweep: "Liquidity Sweep",
  unmitigated_fvg: "Unmitigated FVG",
  continuation: "Continuation",
  other: "Other",
};

function formatAvgRr(value: number | null): string {
  if (value === null) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}R`;
}

interface ConfluenceBadgeProps {
  label: string;
  present: boolean | null;
}

function ConfluenceBadge({ label, present }: ConfluenceBadgeProps) {
  if (present === null) return null;
  const symbol = present ? "✓" : "✗";
  const cls = present
    ? "bg-bull/10 text-bull"
    : "bg-bear/10 text-bear";
  return (
    <span className={`text-[10px] rounded px-1.5 py-0.5 ${cls}`}>
      {label} {symbol}
    </span>
  );
}

interface WinRateBarProps {
  rate: number;
}

function WinRateBar({ rate }: WinRateBarProps) {
  const fill = rate >= 50 ? "#26a69a" : "#ef5350";
  return (
    <div className="h-1.5 rounded-full bg-[#1e1e1e] w-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all"
        style={{ width: `${rate}%`, backgroundColor: fill }}
      />
    </div>
  );
}

interface ComboEntryCardProps {
  entry: IctComboEntry;
  rank: number;
}

function ComboEntryCard({ entry, rank }: ComboEntryCardProps) {
  const setupLabel = SETUP_TYPE_LABELS[entry.setup_type] ?? entry.setup_type;
  const winRate = entry.win_rate ?? 0;
  const winRateStr = entry.win_rate !== null ? `${winRate.toFixed(0)}% win` : "— win";

  return (
    <div className="border border-border rounded-lg p-3 mb-2 hover:border-[#333] transition-colors">
      <div className="flex items-start gap-3">
        <span className="text-2xl font-bold tabular-nums text-[#333] leading-none pt-0.5 w-7 shrink-0">
          {rank}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap mb-1.5">
            <span className="text-sm text-text-primary font-medium">{setupLabel}</span>
            <ConfluenceBadge label="SMT" present={entry.smt_present} />
            <ConfluenceBadge label="TDO" present={entry.tdo_aligned} />
            <span className="text-xs text-text-muted ml-auto">{entry.total} trades</span>
          </div>
          <WinRateBar rate={winRate} />
          <div className="flex items-center gap-3 mt-1.5">
            <span className="text-xs text-text-muted">{winRateStr}</span>
            <span className="text-xs text-text-muted">·</span>
            <span className="text-xs text-text-muted">{formatAvgRr(entry.avg_rr)} avg</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export function IctComboMatrix({ comboMatrix, loading }: IctComboMatrixProps) {
  const [expanded, setExpanded] = useState(false);
  const dim = loading ? "opacity-50" : "";

  const ranked = useMemo(
    () =>
      comboMatrix
        .filter((e) => e.total >= 2)
        .sort((a, b) => (b.win_rate ?? 0) - (a.win_rate ?? 0)),
    [comboMatrix]
  );

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex items-center gap-2 text-xs uppercase tracking-widest text-text-muted hover:text-text-primary py-3 w-full"
      >
        <span>{expanded ? "▼" : "▶"}</span>
        <span>Setup Combinations</span>
        {ranked.length > 0 && (
          <span className="ml-auto text-[10px] normal-case tracking-normal text-text-dim">
            {ranked.length} combos
          </span>
        )}
      </button>

      {expanded && (
        <div className="mt-1">
          {ranked.length === 0 ? (
            <p className="text-text-dim text-sm py-4 text-center">
              Not enough data — need 2+ trades per combination
            </p>
          ) : (
            ranked.map((entry, i) => (
              <ComboEntryCard
                key={`${entry.setup_type}-${String(entry.smt_present)}-${String(entry.tdo_aligned)}`}
                entry={entry}
                rank={i + 1}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
