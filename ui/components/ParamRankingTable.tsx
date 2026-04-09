"use client";

import { useState } from "react";

import type { AnalyticsCorrelation } from "@/lib/types";

type SortCol = "name" | "pvalue";
type SortDir = "asc" | "desc";

function formatPValue(p: number): string {
  if (p < 0.001) return "<0.001";
  if (p < 0.01) return p.toFixed(3);
  return p.toFixed(2);
}

function sortCorrelations(
  items: AnalyticsCorrelation[],
  col: SortCol,
  dir: SortDir
): AnalyticsCorrelation[] {
  const sorted = [...items].sort((a, b) => {
    if (col === "name") return a.param_name.localeCompare(b.param_name);
    return a.p_value - b.p_value;
  });
  return dir === "desc" ? sorted.reverse() : sorted;
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
  const [sortCol, setSortCol] = useState<SortCol>("pvalue");
  const [sortDir, setSortDir] = useState<SortDir>("asc");

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

  return (
    <div>
      {/* Header */}
      <div className="grid grid-cols-[1fr_90px_60px] gap-4 px-4 py-2 border-b border-border">
        <button
          className="label text-left flex items-center gap-1 hover:text-text-primary"
          onClick={() => handleSort("name")}
        >
          Parameter {sortCol === "name" && arrow}
        </button>
        <button
          className="label text-right flex items-center justify-end gap-1 hover:text-text-primary"
          onClick={() => handleSort("pvalue")}
        >
          p-value {sortCol === "pvalue" && arrow}
        </button>
        <span className="label text-center">Sig.</span>
      </div>

      {/* Rows */}
      {sorted.map((c) => {
        const isSelected = selectedParam === c.param_name;
        return (
          <div
            key={c.param_name}
            data-interactive
            role="button"
            tabIndex={0}
            onClick={() => onSelectParam(c.param_name)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelectParam(c.param_name);
              }
            }}
            className={`grid grid-cols-[1fr_90px_60px] gap-4 px-4 py-2.5 border-b border-border cursor-pointer border-l-2 ${
              isSelected
                ? "bg-elevated border-l-primary"
                : "border-l-transparent bg-card hover:bg-surface-raised"
            }`}
          >
            <span className="text-text-primary font-medium">{c.param_name}</span>
            <span
              className={`text-right tabular-nums text-sm ${
                c.significant ? "text-text-primary font-semibold" : "text-text-dim"
              }`}
            >
              {formatPValue(c.p_value)}
            </span>
            <div className="flex justify-center">
              {c.significant ? (
                <span className="text-primary text-sm">&#10003;</span>
              ) : (
                <span className="text-text-dim">--</span>
              )}
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
