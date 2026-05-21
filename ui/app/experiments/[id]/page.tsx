"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { ExperimentResultPanel } from "@/components/ExperimentResultPanel";
import { fetchExperiment, runExperiment } from "@/lib/gatesApi";

import type { Experiment, ExperimentResult } from "@/lib/gatesTypes";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export default function ExperimentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = typeof params.id === "string" ? params.id : "";

  const [experiment, setExperiment] = useState<Experiment | null>(null);
  const [result, setResult] = useState<ExperimentResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchExperiment(id);
      setExperiment(data);
      if (data.last_summary) {
        setResult(data.last_summary as unknown as ExperimentResult);
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load experiment");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { void load(); }, [load]);

  async function handleRun() {
    setRunning(true);
    setError(null);
    try {
      const res = await runExperiment(id);
      setResult(res);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to run experiment");
    } finally {
      setRunning(false);
    }
  }

  if (loading) {
    return <div className="p-6 text-sm text-muted-foreground">Loading...</div>;
  }

  if (!experiment) {
    return <div className="p-6 text-sm text-bear">Experiment not found.</div>;
  }

  return (
    <div className="p-6 max-w-2xl space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-lg font-semibold text-foreground">{experiment.name}</h1>
          {experiment.notes && (
            <p className="text-xs text-muted-foreground mt-0.5">{experiment.notes}</p>
          )}
          <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
            <span>Strategy: {experiment.strategy}</span>
            {experiment.last_run_at && <span>Last run: {formatDate(experiment.last_run_at)}</span>}
          </div>
        </div>
        <Button size="sm" onClick={handleRun} disabled={running}>
          {running ? "Running..." : "Run now"}
        </Button>
      </div>

      <div className="space-y-1.5">
        <div className="label">Conditions ({experiment.conditions.length})</div>
        {experiment.conditions.length === 0 && (
          <p className="text-xs text-muted-foreground">No conditions defined.</p>
        )}
        {experiment.conditions.map((cond, i) => (
          <div key={i} className="flex items-center gap-2 text-xs text-foreground bg-surface border border-border rounded px-3 py-1.5">
            <span className="text-muted-foreground">{cond.param}</span>
            <span className="text-muted-foreground">{cond.op}</span>
            {cond.value !== undefined && <span>{String(cond.value)}</span>}
            {cond.values !== undefined && <span>{cond.values.join(", ")}</span>}
            {cond.low !== undefined && cond.high !== undefined && (
              <span>{cond.low} – {cond.high}</span>
            )}
          </div>
        ))}
      </div>

      {error && <p className="text-xs text-bear">{error}</p>}

      {result && <ExperimentResultPanel result={result} />}

      <Button type="button" variant="outline" size="sm" onClick={() => router.back()}>
        Back
      </Button>
    </div>
  );
}
