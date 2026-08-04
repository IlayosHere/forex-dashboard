"use client";

import { useState } from "react";
import Link from "next/link";
import { ChevronLeft, ChevronRight, ChevronDown } from "lucide-react";

import type { MistakePeriodBucket, MistakeStat } from "@/lib/types";
import type { StatsFiltersParam } from "@/lib/api";

import { useMistakeTimeseries } from "@/lib/useMistakeTimeseries";

type Granularity = "week" | "month";

interface MistakeReviewPanelProps {
  showMoney: boolean;
  filters?: StatsFiltersParam;
}

const MIN_OCCURRENCES_FOR_TREND = 3;
const MIN_STREAK_FOR_BADGE = 3;
const COL = "grid-cols-[1fr_3.5rem_5rem_5rem]";
const MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_FULL = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function toUtcDate(iso: string): Date {
  return new Date(`${iso}T00:00:00Z`);
}

function formatShortDate(iso: string): string {
  const d = toUtcDate(iso);
  return `${MONTH_ABBR[d.getUTCMonth()]} ${d.getUTCDate()}`;
}

function formatPeriodLabel(bucket: MistakePeriodBucket, granularity: Granularity): string {
  if (granularity === "month") {
    const d = toUtcDate(bucket.period_start);
    return `${MONTH_FULL[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  }
  return `${formatShortDate(bucket.period_start)} – ${formatShortDate(bucket.period_end)}`;
}

function countFor(bucket: MistakePeriodBucket | undefined, name: string): number {
  return bucket?.mistakes.find((m) => m.name === name)?.count ?? 0;
}

// Streak = consecutive periods (walking backward from `index`) where the
// mistake's count strictly increased vs. the prior period.
function computeStreak(buckets: MistakePeriodBucket[], index: number, name: string): number {
  let streak = 0;
  let i = index;
  while (i > 0 && countFor(buckets[i], name) > countFor(buckets[i - 1], name)) {
    streak++;
    i--;
  }
  return streak;
}

function streakLabel(streak: number, granularity: Granularity): string {
  return granularity === "week" ? `↑ ${streak} wks` : `↑ ${streak} mo`;
}

// Copied from MistakesPanel's PnlCell (not exported there) — keep in sync by hand.
function PnlCell({ v, showMoney }: { v: number; showMoney: boolean }) {
  const color = v >= 0 ? "text-bull" : "text-bear";
  if (showMoney) {
    const sign = v >= 0 ? "+" : "−";
    return <span className={`text-xs tabular-nums ${color}`}>{sign}${Math.abs(v).toFixed(0)}</span>;
  }
  return <span className={`text-xs tabular-nums ${color}`}>{v >= 0 ? "+" : ""}{v.toFixed(1)}R</span>;
}

function formatTradeDate(iso: string): string {
  if (!iso) return "—";
  const d = toUtcDate(iso);
  return `${MONTH_ABBR[d.getUTCMonth()]} ${d.getUTCDate()}`;
}

function TradeRow({ id, date, symbol, pnl_usd, showMoney }: {
  id: string; date: string; symbol: string; pnl_usd: number | null; showMoney: boolean;
}) {
  return (
    <Link
      href={`/journal/${id}`}
      className="flex items-center justify-between px-2 py-1 rounded hover:bg-[#1a1a1a] transition-colors group"
    >
      <span className="text-xs text-text-muted group-hover:text-text-primary transition-colors">
        {formatTradeDate(date)} · {symbol}
      </span>
      {pnl_usd !== null ? (
        <PnlCell v={pnl_usd} showMoney={showMoney} />
      ) : (
        <span className="text-xs text-text-dim">—</span>
      )}
    </Link>
  );
}

// Deliberately no bull/bear here — those colors are reserved for real P&L.
// Rising mistake frequency lights up the "warning" token; improvement gets no
// reward color, only a neutral muted tone (see CalendarDayCell's BIAS_GLYPH
// precedent for self-describing glyphs over colored dots).
function TrendCell({ current, previous }: { current: number; previous: number }) {
  if (current < MIN_OCCURRENCES_FOR_TREND) {
    return <span className="text-xs text-text-dim tabular-nums">–</span>;
  }
  const delta = current - previous;
  const glyph = delta > 0 ? "▲" : delta < 0 ? "▼" : "–";
  const color = delta > 0 ? "text-warning" : "text-text-muted";
  const deltaLabel = delta === 0 ? "0" : `${delta > 0 ? "+" : "−"}${Math.abs(delta)}`;
  return <span className={`text-xs tabular-nums ${color}`}>{glyph} {deltaLabel}</span>;
}

export function MistakeReviewPanel({ showMoney, filters = {} }: MistakeReviewPanelProps) {
  const [granularity, setGranularity] = useState<Granularity>("week");
  const [offset, setOffset] = useState(0);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const { data, loading } = useMistakeTimeseries(filters, granularity);

  function toggleExpanded(name: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  const maxOffset = data.length > 0 ? data.length - 1 : 0;
  const clampedOffset = Math.min(offset, maxOffset);
  const index = data.length > 0 ? data.length - 1 - clampedOffset : -1;
  const bucket = index >= 0 ? data[index] : null;
  const prevBucket = index > 0 ? data[index - 1] : undefined;

  function handleGranularityChange(next: Granularity) {
    setGranularity(next);
    setOffset(0);
    setExpanded(new Set());
  }

  function handlePrev() {
    setOffset((o) => Math.min(o + 1, maxOffset));
  }

  function handleNext() {
    setOffset((o) => Math.max(o - 1, 0));
  }

  const rows: MistakeStat[] = bucket ? [...bucket.mistakes].sort((a, b) => b.count - a.count) : [];
  const dim = loading ? "opacity-50" : "";
  const periodNoun = granularity === "week" ? "week" : "month";

  return (
    <div className={`bg-card border border-border rounded-lg p-4 ${dim}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={handlePrev}
            disabled={clampedOffset >= maxOffset}
            aria-label="Previous period"
            className="p-1 rounded hover:bg-[#1e1e1e] text-[#777] hover:text-[#e0e0e0] transition-colors disabled:opacity-30 disabled:pointer-events-none"
          >
            <ChevronLeft size={14} />
          </button>
          <span className="text-sm font-medium text-text-primary min-w-[9rem] text-center">
            {bucket ? formatPeriodLabel(bucket, granularity) : "—"}
          </span>
          <button
            type="button"
            onClick={handleNext}
            disabled={clampedOffset <= 0}
            aria-label="Next period"
            className="p-1 rounded hover:bg-[#1e1e1e] text-[#777] hover:text-[#e0e0e0] transition-colors disabled:opacity-30 disabled:pointer-events-none"
          >
            <ChevronRight size={14} />
          </button>
        </div>
        <div className="flex h-7 rounded border border-border bg-surface-input p-0.5 gap-0.5">
          {(["week", "month"] as const).map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => handleGranularityChange(g)}
              className={`px-3 rounded-sm text-xs font-medium transition-colors cursor-pointer ${
                granularity === g
                  ? "bg-bull/20 text-bull ring-1 ring-inset ring-bull/40"
                  : "text-text-dim hover:text-text-muted"
              }`}
            >
              {g === "week" ? "Week" : "Month"}
            </button>
          ))}
        </div>
      </div>

      {bucket && (
        <div className="flex items-center justify-between text-xs text-text-dim mb-3">
          <span>{bucket.total_mistake_trades} mistake trade{bucket.total_mistake_trades === 1 ? "" : "s"}</span>
          <PnlCell v={bucket.total_pnl_usd} showMoney={showMoney} />
        </div>
      )}

      {rows.length === 0 ? (
        <p className="text-text-dim text-sm py-8 text-center">No mistakes logged this {periodNoun}</p>
      ) : (
        <>
          <div className={`grid ${COL} pb-1 mb-1 border-b border-border`}>
            <span className="text-xs text-text-dim">Mistake</span>
            <span className="text-xs text-text-dim text-right">Count</span>
            <span className="text-xs text-text-dim text-right">Trend</span>
            <span className="text-xs text-text-dim text-right">P&L Impact</span>
          </div>
          {rows.map((row) => {
            const streak = computeStreak(data, index, row.name);
            const prevCount = countFor(prevBucket, row.name);
            const isOpen = expanded.has(row.name);
            const hasTrades = row.trades.length > 0;
            return (
              <div key={row.name} className="border-b border-b-[#1a1a1a]">
                <button
                  type="button"
                  onClick={() => hasTrades && toggleExpanded(row.name)}
                  disabled={!hasTrades}
                  aria-expanded={isOpen}
                  className={`grid ${COL} items-center py-1.5 w-full text-left ${
                    hasTrades ? "cursor-pointer hover:bg-[#161616]" : "cursor-default"
                  } transition-colors`}
                >
                  <span className="text-xs text-text-primary truncate pr-2 flex items-center gap-1.5">
                    {hasTrades && (
                      <ChevronDown
                        size={12}
                        className={`shrink-0 text-text-dim transition-transform ${isOpen ? "rotate-0" : "-rotate-90"}`}
                      />
                    )}
                    {row.name}
                    {streak >= MIN_STREAK_FOR_BADGE && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-warning/10 text-warning border border-warning/30 shrink-0">
                        {streakLabel(streak, granularity)}
                      </span>
                    )}
                  </span>
                  <span className="text-xs text-text-muted text-right tabular-nums">{row.count}</span>
                  <div className="flex justify-end"><TrendCell current={row.count} previous={prevCount} /></div>
                  <div className="flex justify-end"><PnlCell v={row.total_pnl_usd} showMoney={showMoney} /></div>
                </button>
                {isOpen && hasTrades && (
                  <div className="pb-2 pl-5 pr-1 flex flex-col gap-0.5">
                    {row.trades.map((t) => (
                      <TradeRow key={t.id} id={t.id} date={t.date} symbol={t.symbol} pnl_usd={t.pnl_usd} showMoney={showMoney} />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </>
      )}
    </div>
  );
}
