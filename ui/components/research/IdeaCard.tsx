"use client";

import { useState } from "react";

import { headline, stageLabel } from "@/lib/researchFormat";
import type { IdeaResult, ResearchIdea } from "@/lib/researchTypes";

import { StatusPill } from "./StatusPill";

function cell(value: number | null, digits = 1, suffix = ""): string {
  return value === null ? "-" : `${value.toFixed(digits)}${suffix}`;
}

function ResultsTable({ results }: { results: IdeaResult[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] text-xs tabular-nums">
        <thead>
          <tr className="text-left text-text-dim">
            <th className="py-1 pr-3 font-normal">Test</th>
            <th className="py-1 pr-3 font-normal">Market</th>
            <th className="py-1 pr-3 text-right font-normal">Trades</th>
            <th className="py-1 pr-3 text-right font-normal">Hit %</th>
            <th className="py-1 pr-3 text-right font-normal">Random %</th>
            <th className="py-1 pr-3 text-right font-normal">Over random</th>
            <th className="py-1 text-right font-normal">z</th>
          </tr>
        </thead>
        <tbody>
          {results.map((r) => (
            <tr key={`${r.label}-${r.market}`} className="border-t border-border text-text-primary">
              <td className="py-1.5 pr-3">{r.label}</td>
              <td className="py-1.5 pr-3 text-text-muted">{r.market ?? "-"}</td>
              <td className="py-1.5 pr-3 text-right">{r.n === null ? "-" : r.n.toLocaleString("en-US")}</td>
              <td className="py-1.5 pr-3 text-right">{cell(r.hit)}</td>
              <td className="py-1.5 pr-3 text-right">{cell(r.control)}</td>
              <td className="py-1.5 pr-3 text-right">{r.excess === null ? "-" : `${r.excess > 0 ? "+" : ""}${r.excess.toFixed(1)}`}</td>
              <td className="py-1.5 text-right">{cell(r.z, 2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface IdeaCardProps {
  idea: ResearchIdea;
  onOpenReport: (path: string) => void;
}

export function IdeaCard({ idea, onOpenReport }: IdeaCardProps) {
  const [open, setOpen] = useState(false);
  const numbers = headline(idea);
  const where = [
    ...idea.trials.map((n) => `trial ${n}`),
    ...idea.log.map((n) => `look ${n}`),
  ].join(", ");

  return (
    <div className="rounded-lg border border-border bg-surface-raised">
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="block w-full px-4 py-3 text-left">
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill status={idea.status} />
          <span className="text-sm font-medium text-text-primary">{idea.name}</span>
          <span className="text-xs text-text-dim">{idea.id}</span>
          <span className="ml-auto text-xs text-text-muted">{stageLabel(idea.stage)}</span>
        </div>
        <p className="mt-1.5 text-xs leading-relaxed text-text-muted">{idea.plain}</p>
        {numbers && <p className="mt-1.5 text-xs tabular-nums text-text-primary">{numbers}</p>}
      </button>

      {open && (
        <div className="space-y-3 border-t border-border px-4 py-3">
          <div>
            <div className="text-xs font-semibold text-text-primary">The rule</div>
            <p className="mt-0.5 text-xs leading-relaxed text-text-muted">{idea.rule}</p>
          </div>
          {idea.results.length > 0 && <ResultsTable results={idea.results} />}
          {idea.years && <p className="text-xs text-text-muted">Years: {idea.years}</p>}
          {idea.notes && <p className="text-xs leading-relaxed text-text-muted">{idea.notes}</p>}
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="text-xs text-text-dim">{where ? `Tested in: ${where}` : ""}</p>
            <button type="button" onClick={() => onOpenReport(idea.report)} className="text-xs text-breakeven hover:underline">
              Read the report
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
