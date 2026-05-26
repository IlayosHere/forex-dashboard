"use client";

import { useState } from "react";
import Link from "next/link";

import { useGateSets } from "@/lib/useGateSets";
import { strategies } from "@/lib/strategies";
import { runAutoOptimize, runAutoRecomputeGrades } from "@/lib/gatesApi";
import type { OptimizeResponse } from "@/lib/gatesApi";
import type { GateSet } from "@/lib/gatesTypes";

function GateSetCard({
  gateSet,
  onActivate,
  onDelete,
}: {
  gateSet: GateSet;
  onActivate: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  const [confirming, setConfirming] = useState(false);

  function handleDelete() {
    if (!confirming) { setConfirming(true); return; }
    onDelete(gateSet.id);
    setConfirming(false);
  }

  return (
    <div
      className={`rounded border p-4 space-y-2 ${
        gateSet.is_active
          ? "border-bull/40 bg-bull/5"
          : "border-border bg-surface"
      }`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-foreground truncate">{gateSet.name}</span>
            {gateSet.is_active && (
              <span className="text-[10px] bg-bull/20 text-bull border border-bull/30 px-1.5 py-0.5 rounded font-medium">
                Active
              </span>
            )}
          </div>
          {gateSet.description && (
            <p className="text-xs text-muted-foreground mt-0.5 truncate">{gateSet.description}</p>
          )}
          <p className="text-xs text-muted-foreground mt-1">
            {gateSet.conditions.length} condition{gateSet.conditions.length !== 1 ? "s" : ""}
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {!gateSet.is_active && (
            <button
              type="button"
              onClick={() => onActivate(gateSet.id)}
              className="text-xs text-bull hover:text-bull/80 transition-colors"
            >
              Activate
            </button>
          )}
          <button
            type="button"
            onClick={handleDelete}
            className={`text-xs transition-colors ${confirming ? "text-bear font-medium" : "text-muted-foreground hover:text-bear"}`}
          >
            {confirming ? "Confirm delete?" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

function pct(v: number | null) {
  if (v == null) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function OptimizeResultPanel({ result, onDismiss }: { result: OptimizeResponse; onDismiss: () => void }) {
  const noConditions = result.conditions_selected.length === 0;
  return (
    <div className={`rounded border p-4 space-y-3 ${noConditions ? "border-border bg-surface" : "border-bull/30 bg-bull/5"}`}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">
          {noConditions ? "No gate improvement found" : `Gate activated — ${result.conditions_selected.length} condition${result.conditions_selected.length !== 1 ? "s" : ""}`}
        </span>
        <button type="button" onClick={onDismiss} className="text-xs text-muted-foreground hover:text-foreground">
          Dismiss
        </button>
      </div>

      {result.reason && (
        <p className="text-xs text-muted-foreground">Reason: {result.reason}</p>
      )}

      <div className="grid grid-cols-4 gap-3">
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Baseline WR</p>
          <p className="text-sm font-medium text-foreground">{pct(result.win_rate_baseline)}</p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Optimized WR</p>
          <p className={`text-sm font-medium ${result.delta != null && result.delta > 0 ? "text-bull" : "text-foreground"}`}>
            {pct(result.win_rate_optimized)}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Delta</p>
          <p className={`text-sm font-medium ${result.delta != null && result.delta > 0 ? "text-bull" : result.delta != null && result.delta < 0 ? "text-bear" : "text-foreground"}`}>
            {result.delta != null ? `${result.delta > 0 ? "+" : ""}${(result.delta * 100).toFixed(1)}%` : "—"}
          </p>
        </div>
        <div>
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Pass rate</p>
          <p className="text-sm font-medium text-foreground">{pct(result.pass_rate)}</p>
        </div>
      </div>

      {result.conditions_selected.length > 0 && (
        <div className="space-y-1">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Conditions</p>
          {result.conditions_selected.map((c, i) => (
            <p key={i} className="text-xs font-mono text-foreground bg-surface rounded px-2 py-1">
              {c.param} <span className="text-muted-foreground">{c.op}</span> {c.value}
            </p>
          ))}
        </div>
      )}

      <p className="text-[10px] text-muted-foreground">
        {result.confirmed_params_found} FDR-confirmed param{result.confirmed_params_found !== 1 ? "s" : ""} analysed
        · {result.pass_count}/{result.total_signals} signals pass
      </p>
    </div>
  );
}

export default function GatesPage() {
  const [activeTab, setActiveTab] = useState(strategies[0].slug);
  const { gateSets, loading, error, activate, remove, refetch } = useGateSets(activeTab);
  const [optimizing, setOptimizing] = useState(false);
  const [optimizeResult, setOptimizeResult] = useState<OptimizeResponse | null>(null);
  const [optimizeError, setOptimizeError] = useState<string | null>(null);

  async function handleAutoOptimize() {
    setOptimizing(true);
    setOptimizeResult(null);
    setOptimizeError(null);
    try {
      const result = await runAutoOptimize({ strategy: activeTab, min_pass_rate: 0.40, dry_run: false });
      setOptimizeResult(result);
      if (result.gate_set_id) {
        await runAutoRecomputeGrades(activeTab);
        refetch();
      }
    } catch (e) {
      setOptimizeError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setOptimizing(false);
    }
  }

  return (
    <div className="p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Gates</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Block signals that fail parameter conditions before they surface in the dashboard.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleAutoOptimize}
            disabled={optimizing}
            className="inline-flex items-center justify-center rounded-md text-sm font-medium h-8 px-3 border border-border text-foreground hover:bg-surface-raised transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {optimizing ? "Optimizing…" : "⚡ Auto-optimize"}
          </button>
          <Link href="/gates/new" className="inline-flex items-center justify-center rounded-md text-sm font-medium h-8 px-3 bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
            + New Gate Set
          </Link>
        </div>
      </div>

      {optimizeError && (
        <div className="mb-4 rounded border border-bear/30 bg-bear/5 px-4 py-3 text-sm text-bear">
          {optimizeError}
        </div>
      )}

      {optimizeResult && (
        <div className="mb-4">
          <OptimizeResultPanel result={optimizeResult} onDismiss={() => setOptimizeResult(null)} />
        </div>
      )}

      <div className="flex gap-0 mb-5 border-b border-border">
        {strategies.map((s) => (
          <button
            key={s.slug}
            type="button"
            onClick={() => { setActiveTab(s.slug); setOptimizeResult(null); setOptimizeError(null); }}
            className={`px-4 py-2 text-sm font-medium transition-colors -mb-px ${
              activeTab === s.slug
                ? "text-bull border-b-2 border-bull"
                : "text-muted-foreground hover:text-foreground border-b-2 border-transparent"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      {loading && (
        <p className="text-sm text-muted-foreground py-8 text-center">Loading...</p>
      )}

      {error && (
        <p className="text-sm text-bear py-8 text-center">Error: {error}</p>
      )}

      {!loading && !error && gateSets.length === 0 && (
        <div className="text-center py-12 border border-dashed border-border rounded">
          <p className="text-sm text-muted-foreground mb-2">No gate sets for this strategy.</p>
          <p className="text-xs text-muted-foreground mb-4">
            Create a gate set to automatically block low-quality signals.
          </p>
          <Link href="/gates/new" className="inline-flex items-center justify-center rounded-md text-sm font-medium h-8 px-3 border border-border text-foreground hover:bg-surface-raised transition-colors">
            Create first gate set
          </Link>
        </div>
      )}

      {!loading && !error && gateSets.length > 0 && (
        <div className="space-y-3">
          {gateSets.map((gs) => (
            <GateSetCard
              key={gs.id}
              gateSet={gs}
              onActivate={activate}
              onDelete={remove}
            />
          ))}
        </div>
      )}
    </div>
  );
}
