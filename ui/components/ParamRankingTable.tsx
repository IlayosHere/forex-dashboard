"use client";

import { useEffect, useRef, useState } from "react";

import { StrengthMeter } from "@/components/StrengthMeter";

import type { AnalyticsCorrelation } from "@/lib/types";

import { rankOfLevel } from "@/lib/analyticsLevels";
import { getParamLabel, getParamMeta } from "@/lib/analyticsParamMeta";

type SortCol = "name" | "strength";
type SortDir = "asc" | "desc";
type FdrStatus = AnalyticsCorrelation["fdr_status"];

const FDR_BADGE: Record<FdrStatus, { label: string; className: string } | null> = {
  confirmed: { label: "Confirmed", className: "bg-green-500/15 text-green-400 border border-green-500/30" },
  exploratory: { label: "Exploratory", className: "bg-amber-500/15 text-amber-400 border border-amber-500/30" },
  insufficient_data: null,
};

const SAMPLE_SIZE_CLASS = (n: number): string => {
  if (n >= 100) return "bg-green-500/15 text-green-400 border border-green-500/30";
  if (n >= 50) return "bg-amber-500/15 text-amber-400 border border-amber-500/30";
  return "bg-red-500/15 text-red-400 border border-red-500/30";
};

const SAMPLE_SIZE_TOOLTIP = (n: number): string =>
  n < 50 ? "Results below 50 signals are exploratory only" : `${n} resolved signals`;

function sortCorrelations(
  items: AnalyticsCorrelation[],
  col: SortCol,
  dir: SortDir
): AnalyticsCorrelation[] {
  const sorted = [...items].sort((a, b) => {
    if (col === "name") {
      const cmp = a.param_name.localeCompare(b.param_name);
      return dir === "asc" ? cmp : -cmp;
    }
    const rankDiff = rankOfLevel(b.level) - rankOfLevel(a.level);
    if (rankDiff !== 0) return dir === "desc" ? rankDiff : -rankDiff;
    const deltaDiff = Math.abs(b.delta ?? 0) - Math.abs(a.delta ?? 0);
    return dir === "desc" ? deltaDiff : -deltaDiff;
  });
  return sorted;
}

function CiBar({ delta, ciLo, ciHi }: { delta: number; ciLo: number; ciHi: number }) {
  const range = 0.4;
  const toPercent = (v: number) => Math.max(0, Math.min(100, ((v + range) / (2 * range)) * 100));

  const zeroPos = toPercent(0);
  const loPos = toPercent(ciLo);
  const hiPos = toPercent(ciHi);
  const barLeft = Math.min(loPos, zeroPos);
  const barWidth = Math.abs(hiPos - loPos);
  const positive = delta >= 0;
  const straddles = ciLo < 0 && ciHi > 0;
  const barColor = straddles ? "#6b7280" : positive ? "#22c55e" : "#ef4444";

  return (
    <div className="relative h-3 w-full bg-elevated rounded-sm overflow-hidden">
      <div
        className="absolute top-0 bottom-0 opacity-60 rounded-sm"
        style={{ left: `${barLeft}%`, width: `${barWidth}%`, backgroundColor: barColor }}
      />
      <div
        className="absolute top-0 bottom-0 w-px bg-border"
        style={{ left: `${zeroPos}%` }}
      />
    </div>
  );
}

interface ParamRankingTableProps {
  correlations: AnalyticsCorrelation[];
  selectedParam: string | null;
  onSelectParam: (name: string) => void;
  totalResolved?: number;
}

export function ParamRankingTable({
  correlations,
  selectedParam,
  onSelectParam,
  totalResolved,
}: ParamRankingTableProps) {
  const [sortCol, setSortCol] = useState<SortCol>("strength");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [focusedIndex, setFocusedIndex] = useState<number | null>(null);
  const rowRefs = useRef<(HTMLDivElement | null)[]>([]);

  function handleSort(col: SortCol) {
    if (sortCol === col) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col);
      setSortDir("asc");
    }
  }

  const sorted = sortCorrelations(correlations, sortCol, sortDir);
  const arrow = sortDir === "asc" ? "▴" : "▾";

  useEffect(() => {
    rowRefs.current = rowRefs.current.slice(0, sorted.length);
  }, [sorted.length]);

  function handleKeyDown(e: React.KeyboardEvent, index: number) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const next = Math.min(index + 1, sorted.length - 1);
      setFocusedIndex(next);
      rowRefs.current[next]?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      const prev = Math.max(index - 1, 0);
      setFocusedIndex(prev);
      rowRefs.current[prev]?.focus();
    } else if (e.key === "Home") {
      e.preventDefault();
      setFocusedIndex(0);
      rowRefs.current[0]?.focus();
    } else if (e.key === "End") {
      e.preventDefault();
      const last = sorted.length - 1;
      setFocusedIndex(last);
      rowRefs.current[last]?.focus();
    }
  }

  return (
    <div>
      {/* Sample size badge */}
      {totalResolved !== undefined && (
        <div className="px-4 py-2 border-b border-border flex items-center gap-2">
          <span
            className={`inline-flex items-center px-2 h-5 rounded-full text-[10px] uppercase tracking-wider font-semibold ${SAMPLE_SIZE_CLASS(totalResolved)}`}
            title={SAMPLE_SIZE_TOOLTIP(totalResolved)}
          >
            {totalResolved} signals
          </span>
        </div>
      )}

      {/* Header */}
      <div className="grid grid-cols-[1fr_90px] gap-4 px-4 py-2 border-b border-border">
        <button
          className="label text-left flex items-center gap-1 hover:text-text-primary"
          onClick={() => handleSort("name")}
        >
          Parameter {sortCol === "name" && arrow}
        </button>
        <button
          className="label text-right flex items-center justify-end gap-1 hover:text-text-primary"
          onClick={() => handleSort("strength")}
        >
          Strength {sortCol === "strength" && arrow}
        </button>
      </div>

      {/* Rows */}
      {sorted.map((c, index) => {
        const isSelected = selectedParam === c.param_name;
        const fdrBadge = FDR_BADGE[c.fdr_status ?? "insufficient_data"];
        const hasCi = c.ci_lo !== null && c.ci_hi !== null && c.delta !== null;

        return (
          <div
            key={c.param_name}
            ref={(el) => { rowRefs.current[index] = el; }}
            data-interactive
            role="button"
            tabIndex={0}
            title={getParamMeta(c.param_name)?.description ?? c.param_name}
            onClick={() => onSelectParam(c.param_name)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelectParam(c.param_name);
              } else {
                handleKeyDown(e, index);
              }
            }}
            onFocus={() => setFocusedIndex(index)}
            className={`grid grid-cols-[1fr_90px] gap-4 px-4 py-2.5 border-b border-border cursor-pointer border-l-2 ${
              isSelected
                ? "bg-elevated border-l-primary"
                : "border-l-transparent bg-card hover:bg-surface-raised"
            }`}
          >
            <div className="flex flex-col gap-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-text-primary font-medium" title={c.param_name}>
                  {getParamLabel(c.param_name)}
                </span>
                {fdrBadge && (
                  <span
                    className={`inline-flex items-center px-1.5 h-4 rounded-full text-[9px] uppercase tracking-wider font-semibold shrink-0 ${fdrBadge.className}`}
                  >
                    {fdrBadge.label}
                  </span>
                )}
              </div>
              {hasCi && (
                <CiBar
                  delta={c.delta as number}
                  ciLo={c.ci_lo as number}
                  ciHi={c.ci_hi as number}
                />
              )}
            </div>
            <div className="flex justify-end items-start pt-0.5">
              <StrengthMeter level={c.level} pValue={c.p_value} size="sm" />
            </div>
          </div>
        );
      })}

      {sorted.length === 0 && (
        <div className="px-4 py-8 text-center text-text-muted text-sm">
          No parameters analyzed yet
        </div>
      )}
    </div>
  );
}
