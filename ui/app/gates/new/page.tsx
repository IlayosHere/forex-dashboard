"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ConditionBuilder } from "@/components/ConditionBuilder";
import { useGateSets } from "@/lib/useGateSets";
import { useGatePreview } from "@/lib/useGatePreview";
import { strategies } from "@/lib/strategies";

import type { GateCondition } from "@/lib/gatesTypes";

const SELECT_CLASSES =
  "h-9 w-full rounded border border-border bg-surface-input text-foreground text-sm px-3 focus:outline-none focus:ring-1 focus:ring-ring";

export default function NewGateSetPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [strategy, setStrategy] = useState(strategies[0].slug);
  const [conditions, setConditions] = useState<GateCondition[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { create } = useGateSets();
  const { preview, loading: previewLoading } = useGatePreview(strategy, conditions);

  async function handleSave() {
    if (!name.trim()) { setError("Name is required."); return; }
    if (conditions.some((c) => !c.param)) { setError("All conditions must have a parameter selected."); return; }

    setSaving(true);
    setError(null);
    try {
      await create({ strategy, name: name.trim(), description: description.trim() || null, conditions });
      router.push("/gates");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save gate set");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="p-6 max-w-2xl">
      <div className="mb-6">
        <h1 className="text-lg font-semibold text-foreground">New Gate Set</h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Define conditions to block signals that do not meet your criteria.
        </p>
      </div>

      <div className="space-y-4">
        <div>
          <label className="label block mb-1.5" htmlFor="gate-name">Name</label>
          <Input
            id="gate-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. High confidence only"
            className="h-9"
          />
        </div>

        <div>
          <label className="label block mb-1.5" htmlFor="gate-description">Description</label>
          <textarea
            id="gate-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="Optional description..."
            className="w-full rounded border border-border bg-surface-input text-foreground text-sm px-3 py-2 focus:outline-none focus:ring-1 focus:ring-ring resize-none"
          />
        </div>

        <div>
          <label className="label block mb-1.5" htmlFor="gate-strategy">Strategy</label>
          <select
            id="gate-strategy"
            value={strategy}
            onChange={(e) => setStrategy(e.target.value)}
            className={SELECT_CLASSES}
          >
            {strategies.map((s) => (
              <option key={s.slug} value={s.slug}>{s.label}</option>
            ))}
          </select>
        </div>

        <div>
          <div className="label mb-2">Conditions</div>
          <ConditionBuilder
            conditions={conditions}
            onChange={setConditions}
            strategy={strategy}
            preview={preview}
            previewLoading={previewLoading}
          />
        </div>

        {error && <p className="text-xs text-bear">{error}</p>}

        <div className="flex items-center gap-3 pt-2">
          <Button onClick={handleSave} disabled={saving} size="sm">
            {saving ? "Saving..." : "Save Gate Set"}
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
