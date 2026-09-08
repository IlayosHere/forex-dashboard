"use client";

import { useEffect, useState } from "react";

import { HolidayWarningBanner } from "@/components/HolidayWarningBanner";
import { ScenarioCard } from "@/components/ScenarioCard";
import { ScenarioForm } from "@/components/ScenarioForm";

import type {
  DailyBias,
  MarketClosure,
  PlanUpsertRequest,
  PremarketPlan,
  ScenarioCreateRequest,
  ScenarioOutcome,
  ScenarioUpdateRequest,
} from "@/lib/types";

interface PreMarketSectionProps {
  plan: PremarketPlan | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  closure: MarketClosure | null;
  savePlan: (data: PlanUpsertRequest) => Promise<void>;
  addScenario: (data: ScenarioCreateRequest) => Promise<void>;
  updateScenario: (scenarioId: string, data: ScenarioUpdateRequest) => Promise<void>;
  removeScenario: (scenarioId: string) => Promise<void>;
}

const BIAS_OPTIONS: { value: DailyBias; label: string; activeColor: string }[] = [
  { value: "bullish", label: "Bullish", activeColor: "#26a69a" },
  { value: "bearish", label: "Bearish", activeColor: "#ef5350" },
  { value: "neutral", label: "Neutral", activeColor: "#777777" },
];

export function PreMarketSection({
  plan, loading, saving, error, closure, savePlan, addScenario, updateScenario, removeScenario,
}: PreMarketSectionProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [reconsidering, setReconsidering] = useState(false);

  const bias = plan?.daily_bias ?? null;
  const holidayAck = plan?.holiday_ack ?? null;
  const isGated = closure?.closure_type === "early_close" && (holidayAck == null || reconsidering);

  useEffect(() => setReconsidering(false), [closure?.date]);

  async function handleBiasClick(value: DailyBias) {
    await savePlan({ daily_bias: bias === value ? null : value });
  }

  async function handleHolidayAck(ack: "stood_down" | "proceeded") {
    setReconsidering(false);
    await savePlan({
      weekly_dealing_range: plan?.weekly_dealing_range ?? null,
      weekly_dol: plan?.weekly_dol ?? null,
      weekly_opening_gap: plan?.weekly_opening_gap ?? null,
      daily_bias: plan?.daily_bias ?? null,
      daily_bias_signals: plan?.daily_bias_signals ?? {},
      h4_pd_array: plan?.h4_pd_array ?? null,
      h4_pd_location: plan?.h4_pd_location ?? null,
      h1_zone: plan?.h1_zone ?? null,
      h1_structure: plan?.h1_structure ?? null,
      ltf_notes: plan?.ltf_notes ?? null,
      narrative: plan?.narrative ?? "",
      holiday_ack: ack,
    });
  }

  async function handleSaveEdit(scenarioId: string, data: ScenarioCreateRequest) {
    const scenario = plan?.scenarios.find((s) => s.id === scenarioId);
    await updateScenario(scenarioId, { ...data, outcome_status: scenario?.outcome_status ?? null });
    setEditingId(null);
  }

  function handleSetOutcome(scenarioId: string, outcome: ScenarioOutcome | null) {
    const scenario = plan?.scenarios.find((s) => s.id === scenarioId);
    if (!scenario) return;
    void updateScenario(scenarioId, {
      reaction_setup_type: scenario.reaction_setup_type,
      reaction_setup_detail: scenario.reaction_setup_detail,
      target_level_type: scenario.target_level_type,
      target_level_detail: scenario.target_level_detail,
      notes: scenario.notes,
      outcome_status: outcome,
    });
  }

  return (
    <div className="space-y-4">
      {loading && <p className="text-sm text-text-muted">Loading…</p>}
      {error && <p className="text-bear text-xs">{error}</p>}

      {closure && (
        <HolidayWarningBanner
          closure={closure}
          holidayAck={holidayAck}
          showAckChoice={reconsidering || holidayAck == null}
          saving={saving}
          onChooseAck={handleHolidayAck}
          onReconsider={() => setReconsidering(true)}
        />
      )}

      {!isGated && (
        <>
          <div className="border border-border rounded-lg p-4 bg-card space-y-3">
            <label className="block text-xs text-text-muted mb-1">Today&apos;s bias</label>
            <div className="flex gap-1.5">
              {BIAS_OPTIONS.map((opt) => {
                const isActive = bias === opt.value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => handleBiasClick(opt.value)}
                    disabled={saving}
                    className={`px-3 py-1.5 rounded text-xs font-medium border transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
                      isActive ? "border-current" : "border-border text-text-muted hover:border-[#444] hover:text-text-primary"
                    }`}
                    style={isActive ? { color: opt.activeColor, backgroundColor: `${opt.activeColor}18` } : undefined}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="border border-border rounded-lg p-4 bg-card">
            <p className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">Add Scenario</p>
            <ScenarioForm onAdd={addScenario} saving={saving} />
          </div>

          {(plan?.scenarios.length ?? 0) > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-text-muted uppercase tracking-wider">Today&apos;s Scenarios</p>
              {plan?.scenarios.map((s, i) => (
                <ScenarioCard
                  key={s.id}
                  scenario={s}
                  index={i}
                  saving={saving}
                  isEditing={editingId === s.id}
                  onEdit={() => setEditingId(s.id)}
                  onSaveEdit={(data) => handleSaveEdit(s.id, data)}
                  onCancelEdit={() => setEditingId(null)}
                  onDelete={removeScenario}
                  onSetOutcome={handleSetOutcome}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
