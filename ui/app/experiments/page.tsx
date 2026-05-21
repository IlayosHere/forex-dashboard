"use client";

import { useState } from "react";
import Link from "next/link";

import { useExperiments } from "@/lib/useExperiments";
import { strategies } from "@/lib/strategies";

import type { Experiment } from "@/lib/gatesTypes";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return <span className="text-muted-foreground">—</span>;
  const sign = delta > 0 ? "+" : "";
  const cls = delta > 0 ? "text-bull" : delta < 0 ? "text-bear" : "text-muted-foreground";
  return <span className={`font-semibold ${cls}`}>{sign}{(delta * 100).toFixed(1)}%</span>;
}

function ExperimentCard({
  experiment,
  onDelete,
}: {
  experiment: Experiment;
  onDelete: (id: string) => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const summary = experiment.last_summary as Record<string, unknown> | null;
  const delta = typeof summary?.delta_vs_baseline === "number" ? summary.delta_vs_baseline : null;
  const passingCount = typeof summary?.passing_signals === "number" ? summary.passing_signals : null;

  function handleDelete() {
    if (!confirming) { setConfirming(true); return; }
    onDelete(experiment.id);
    setConfirming(false);
  }

  return (
    <div className="rounded border border-border bg-surface p-4 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-medium text-sm text-foreground truncate">{experiment.name}</div>
          {experiment.notes && (
            <p className="text-xs text-muted-foreground mt-0.5 truncate">{experiment.notes}</p>
          )}
          <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
            <span>{experiment.conditions.length} condition{experiment.conditions.length !== 1 ? "s" : ""}</span>
            {experiment.last_run_at && (
              <span>Last run {formatDate(experiment.last_run_at)}</span>
            )}
          </div>
        </div>

        <div className="shrink-0 text-right space-y-0.5">
          {delta !== null && <DeltaBadge delta={delta} />}
          {passingCount !== null && (
            <div className="text-xs text-muted-foreground">{String(passingCount)} passing</div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 pt-1">
        <Link
          href={`/experiments/${experiment.id}`}
          className="text-xs text-bull hover:text-bull/80 transition-colors"
        >
          View / Run
        </Link>
        <button
          type="button"
          onClick={handleDelete}
          className={`text-xs transition-colors ${confirming ? "text-bear font-medium" : "text-muted-foreground hover:text-bear"}`}
        >
          {confirming ? "Confirm delete?" : "Delete"}
        </button>
      </div>
    </div>
  );
}

export default function ExperimentsPage() {
  const [activeTab, setActiveTab] = useState(strategies[0].slug);
  const { experiments, loading, error, remove } = useExperiments(activeTab);

  return (
    <div className="p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Experiments</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Backtest condition filters against historical signals and compare win rates.
          </p>
        </div>
        <Link href="/experiments/new" className="inline-flex items-center justify-center rounded-md text-sm font-medium h-8 px-3 bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
          + New Experiment
        </Link>
      </div>

      <div className="flex gap-0 mb-5 border-b border-border">
        {strategies.map((s) => (
          <button
            key={s.slug}
            type="button"
            onClick={() => setActiveTab(s.slug)}
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

      {!loading && !error && experiments.length === 0 && (
        <div className="text-center py-12 border border-dashed border-border rounded">
          <p className="text-sm text-muted-foreground mb-2">No experiments for this strategy.</p>
          <p className="text-xs text-muted-foreground mb-4">
            Create an experiment to backtest condition filters and find an edge.
          </p>
          <Link href="/experiments/new" className="inline-flex items-center justify-center rounded-md text-sm font-medium h-8 px-3 border border-border text-foreground hover:bg-surface-raised transition-colors">
            Create first experiment
          </Link>
        </div>
      )}

      {!loading && !error && experiments.length > 0 && (
        <div className="space-y-3">
          {experiments.map((exp) => (
            <ExperimentCard
              key={exp.id}
              experiment={exp}
              onDelete={remove}
            />
          ))}
        </div>
      )}
    </div>
  );
}
