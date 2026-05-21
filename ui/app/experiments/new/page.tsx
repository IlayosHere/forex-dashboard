"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConditionBuilder } from "@/components/ConditionBuilder";
import { ExperimentResultPanel } from "@/components/ExperimentResultPanel";
import { useExperiments } from "@/lib/useExperiments";
import { useExperimentEvaluate } from "@/lib/useExperimentEvaluate";
import { runExperiment } from "@/lib/gatesApi";
import { strategies } from "@/lib/strategies";

import type { GateCondition } from "@/lib/gatesTypes";

const SELECT_CLASSES =
  "h-9 w-full rounded border border-border bg-surface-input text-foreground text-sm px-3 focus:outline-none focus:ring-1 focus:ring-ring";

export default function NewExperimentPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [strategy, setStrategy] = useState(strategies[0].slug);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [notes, setNotes] = useState("");
  const [conditions, setConditions] = useState<GateCondition[]>([]);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const { create } = useExperiments();
  const { result, loading: evaluating, error: evalError, evaluate } = useExperimentEvaluate();

  async function handleEvaluate() {
    if (conditions.length === 0) return;
    await evaluate({
      strategy,
      conditions,
      date_from: dateFrom || null,
      date_to: dateTo || null,
    });
  }

  async function handleRunAndSave() {
    if (!name.trim()) { setFormError("Name is required."); return; }
    if (conditions.some((c) => !c.param)) { setFormError("All conditions must have a parameter selected."); return; }

    setSaving(true);
    setFormError(null);
    try {
      const exp = await create({
        name: name.trim(),
        strategy,
        conditions,
        date_from: dateFrom || null,
        date_to: dateTo || null,
        notes: notes.trim() || null,
      });
      await runExperiment(exp.id);
      router.push("/experiments");
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Failed to save experiment");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-foreground">New Experiment</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Apply condition filters to historical signals and measure win rate vs baseline.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="label block mb-1.5" htmlFor="exp-name">Name</label>
          <Input
            id="exp-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Bullish FVG with momentum"
            className="h-9"
          />
        </div>

        <div>
          <label className="label block mb-1.5" htmlFor="exp-strategy">Strategy</label>
          <select
            id="exp-strategy"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className={SELECT_CLASSES}
          >
            {strategies.map((s) => (
              <option key={s.slug} value={s.slug}>{s.label}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label block mb-1.5" htmlFor="exp-from">Date from</label>
            <Input
              id="exp-from"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="h-9"
            />
          </div>
          <div>
            <label className="label block mb-1.5" htmlFor="exp-to">Date to</label>
            <Input
              id="exp-to"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="h-9"
            />
          </div>
        </div>

        <div>
          <label className="label block mb-1.5" htmlFor="exp-notes">Notes</label>
          <textarea
            id="exp-notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Optional notes..."
            className="w-full rounded border border-border bg-surface-input text-foreground text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-ring resize-none"
          />
        </div>

        <div>
          <div className="label mb-2">Conditions</div>
          <ConditionBuilder
            conditions={conditions}
            onChange={setConditions}
            strategy={strategy}
          />
        </div>

        {conditions.length > 0 && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={handleEvaluate}
            disabled={evaluating}
          >
            {evaluating ? "Evaluating..." : "Preview result"}
          </Button>
        )}

        {evalError && <p className="text-xs text-bear">{evalError}</p>}

        {result && <ExperimentResultPanel result={result} />}

        {formError && <p className="text-xs text-bear">{formError}</p>}

        <div className="flex items-center gap-3 pt-2">
          <Button onClick={handleRunAndSave} disabled={saving} size="sm">
            {saving ? "Saving..." : "Run & Save"}
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => router.back()}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
