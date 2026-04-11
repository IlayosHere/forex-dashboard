"use client";

import { useEffect, useRef, useState } from "react";

import { StrengthMeter } from "@/components/StrengthMeter";

import type { AnalyticsCorrelation } from "@/lib/types";

import { rankOfLevel } from "@/lib/analyticsLevels";
import { getParamLabel, getParamMeta } from "@/lib/analyticsParamMeta";

type SortCol = "name" | "strength";
type SortDir = "asc" | "desc";

function sortCorrelations(
  items: AnalyticsCorrelation[],
  col: SortCol,
  dir: SortDir
): AnalyticsCorrelation[] {
  // For "strength" col: desc = strongest first (highest rank at top).
  // For "name" col: asc = A→Z, desc = Z→A.
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

interface ParamRankingTableProps {
  correlations: AnalyticsCorrelation[];
  selectedParam: string | null;
  onSelectParam: (name: string) => void;
}

export function ParamRankingTable({
  correlations,
  selectedParam,
  onSelectParam,
}: ParamRankingTableProps) {
  const [sortCol, setSortCol] = useState<SortCol>("strength");
  // "desc" = strongest first for strength col, Z→A for name col.
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
  const arrow = sortDir === "asc" ? "\u25B4" : "\u25BE";

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
            <span className="text-text-primary font-medium" title={c.param_name}>
              {getParamLabel(c.param_name)}
            </span>
            <div className="flex justify-end items-center">
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
