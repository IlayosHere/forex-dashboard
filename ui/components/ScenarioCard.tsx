"use client";

import Link from "next/link";

import { ScenarioForm } from "@/components/ScenarioForm";

import type { ScenarioCreateRequest, ScenarioOutcome, PlanScenario } from "@/lib/types";

interface ScenarioCardProps {
  scenario: PlanScenario;
  index: number;
  saving: boolean;
  isEditing: boolean;
  onEdit: () => void;
  onSaveEdit: (data: ScenarioCreateRequest) => Promise<void>;
  onCancelEdit: () => void;
  onDelete: (scenarioId: string) => void;
  onSetOutcome: (scenarioId: string, outcome: ScenarioOutcome | null) => void;
}

interface RowProps {
  label: string;
  value: string | null;
}

const OUTCOME_OPTIONS: { value: ScenarioOutcome; label: string; activeColor: string }[] = [
  { value: "played_out", label: "Played Out", activeColor: "#26a69a" },
  { value: "partial", label: "Partial", activeColor: "#e6a800" },
  { value: "invalidated", label: "Invalidated", activeColor: "#ef5350" },
  { value: "never_triggered", label: "Never Triggered", activeColor: "#777777" },
];

function joinParts(parts: (string | null)[]): string | null {
  const filtered = parts.filter((p): p is string => Boolean(p));
  return filtered.length > 0 ? filtered.join(" · ") : null;
}

function Row({ label, value }: RowProps) {
  if (!value) return null;
  return (
    <div className="flex gap-2 text-xs">
      <span className="text-text-muted w-28 shrink-0">{label}</span>
      <span className="text-text-primary">{value}</span>
    </div>
  );
}

export function ScenarioCard({
  scenario, index, saving, isEditing, onEdit, onSaveEdit, onCancelEdit, onDelete, onSetOutcome,
}: ScenarioCardProps) {
  if (isEditing) {
    return (
      <div className="border border-bull/40 rounded-lg p-3 bg-card space-y-1.5">
        <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider mb-1">
          Editing Scenario {index + 1}
        </p>
        <ScenarioForm editing={scenario} onSaveEdit={onSaveEdit} onCancelEdit={onCancelEdit} saving={saving} />
      </div>
    );
  }

  return (
    <div className="border border-border rounded-lg p-3 bg-card space-y-1.5">
      <div className="flex items-center justify-between mb-1">
        <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
          Scenario {index + 1}
        </p>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onEdit}
            className="text-[11px] text-text-muted hover:text-text-primary cursor-pointer transition-colors"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => onDelete(scenario.id)}
            className="text-[11px] text-text-muted hover:text-bear cursor-pointer transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
      <Row label="Area" value={joinParts([scenario.reaction_setup_type, scenario.reaction_setup_detail])} />
      <Row label="Target / DOL" value={joinParts([scenario.target_level_type, scenario.target_level_detail])} />
      <Row label="Notes" value={scenario.notes || null} />

      <div className="flex items-center justify-between gap-2 pt-1.5 mt-1.5 border-t border-border">
        <div className="flex flex-wrap gap-1">
          {OUTCOME_OPTIONS.map((o) => {
            const isActive = scenario.outcome_status === o.value;
            return (
              <button
                key={o.value}
                type="button"
                onClick={() => onSetOutcome(scenario.id, isActive ? null : o.value)}
                className={`px-1.5 py-0.5 rounded text-[10px] font-medium border transition-colors cursor-pointer ${
                  isActive ? "border-current" : "border-border text-text-muted hover:border-[#444] hover:text-text-primary"
                }`}
                style={isActive ? { color: o.activeColor, backgroundColor: `${o.activeColor}18` } : undefined}
              >
                {o.label}
              </button>
            );
          })}
        </div>
        <Link
          href={`/journal/new?scenario=${scenario.id}`}
          className="text-[11px] text-text-muted hover:text-bull transition-colors shrink-0"
        >
          Log Trade →
        </Link>
      </div>
    </div>
  );
}
