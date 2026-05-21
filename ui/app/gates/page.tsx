"use client";

import { useState } from "react";
import Link from "next/link";

import { useGateSets } from "@/lib/useGateSets";
import { strategies } from "@/lib/strategies";

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

export default function GatesPage() {
  const [activeTab, setActiveTab] = useState(strategies[0].slug);
  const { gateSets, loading, error, activate, remove } = useGateSets(activeTab);

  return (
    <div className="p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-lg font-semibold text-foreground">Gates</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Block signals that fail parameter conditions before they surface in the dashboard.
          </p>
        </div>
        <Link href="/gates/new" className="inline-flex items-center justify-center rounded-md text-sm font-medium h-8 px-3 bg-primary text-primary-foreground hover:bg-primary/90 transition-colors">
          + New Gate Set
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
