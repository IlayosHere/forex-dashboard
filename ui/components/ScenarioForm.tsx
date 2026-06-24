"use client";

import { useState } from "react";

import type { PlanScenario, ScenarioCreateRequest } from "@/lib/types";

interface ScenarioFormProps {
  /** Required for add mode; unused when `editing` is set. */
  onAdd?: (data: ScenarioCreateRequest) => Promise<void>;
  saving: boolean;
  /** When set, the form edits this scenario in place instead of creating a new one. */
  editing?: PlanScenario;
  onSaveEdit?: (data: ScenarioCreateRequest) => Promise<void>;
  onCancelEdit?: () => void;
}

const SELECT_CLASS =
  "bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull w-full h-8 cursor-pointer transition-colors";
const LABEL_CLASS = "block text-xs text-text-muted mb-1";

// Liquidity level taxonomy for the target/DOL — external liquidity (a high/low) or
// internal liquidity (an FVG).
const LEVEL_TYPE_OPTIONS = [
  { value: "session_high_low", label: "Session High/Low" },
  { value: "htf_high_low", label: "HTF High/Low" },
  { value: "fvg", label: "FVG" },
  { value: "other", label: "Other" },
];

const LEVEL_DETAIL_OPTIONS: Record<string, { value: string; label: string }[]> = {
  session_high_low: [
    { value: "asia_high", label: "Asia High" },
    { value: "asia_low", label: "Asia Low" },
    { value: "london_high", label: "London High" },
    { value: "london_low", label: "London Low" },
    { value: "data_high", label: "Data High" },
    { value: "data_low", label: "Data Low" },
    { value: "other", label: "Other" },
  ],
  htf_high_low: [
    { value: "1m_high", label: "1M High" },
    { value: "1m_low", label: "1M Low" },
    { value: "5m_high", label: "5M High" },
    { value: "5m_low", label: "5M Low" },
    { value: "15m_high", label: "15M High" },
    { value: "15m_low", label: "15M Low" },
    { value: "1h_high", label: "1H High" },
    { value: "1h_low", label: "1H Low" },
    { value: "4h_high", label: "4H High" },
    { value: "4h_low", label: "4H Low" },
    { value: "1d_high", label: "1D High" },
    { value: "1d_low", label: "1D Low" },
    { value: "1w_high", label: "1W High" },
    { value: "1w_low", label: "1W Low" },
    { value: "ath", label: "ATH" },
    { value: "other", label: "Other" },
  ],
  fvg: [
    { value: "3m", label: "3M FVG" },
    { value: "5m", label: "5M FVG" },
    { value: "15m", label: "15M FVG" },
    { value: "30m", label: "30M FVG" },
    { value: "1h", label: "1H FVG" },
    { value: "2h", label: "2H FVG" },
    { value: "4h", label: "4H FVG" },
    { value: "other", label: "Other" },
  ],
};

// Mirrors the trade journal's setup type/detail taxonomy (ict_setup_type/ict_setup_detail)
// so a scenario's reaction area can later be compared directly to the trade it produced.
// Kept as its own explicit list — LIQUIDITY_SWEEP_DETAILS is not identical to LEVEL_DETAIL_OPTIONS
// (e.g. it has "gap_fill" and no 1w/ath), so don't derive one from the other.
const REACTION_DETAIL_OPTIONS: Record<string, { value: string; label: string }[]> = {
  liquidity_sweep: [
    { value: "london_high", label: "London High" },
    { value: "london_low", label: "London Low" },
    { value: "asia_high", label: "Asia High" },
    { value: "asia_low", label: "Asia Low" },
    { value: "data_high", label: "Data High" },
    { value: "data_low", label: "Data Low" },
    { value: "1m_high", label: "1M High" },
    { value: "1m_low", label: "1M Low" },
    { value: "5m_high", label: "5M High" },
    { value: "5m_low", label: "5M Low" },
    { value: "15m_high", label: "15M High" },
    { value: "15m_low", label: "15M Low" },
    { value: "1h_high", label: "1H High" },
    { value: "1h_low", label: "1H Low" },
    { value: "4h_high", label: "4H High" },
    { value: "4h_low", label: "4H Low" },
    { value: "1d_high", label: "1D High" },
    { value: "1d_low", label: "1D Low" },
    { value: "gap_fill", label: "Gap Fill" },
    { value: "other", label: "Other" },
  ],
  unmitigated_fvg: [
    { value: "15m", label: "15M FVG" },
    { value: "30m", label: "30M FVG" },
    { value: "1h", label: "1H FVG" },
    { value: "2h", label: "2H FVG" },
    { value: "4h", label: "4H FVG" },
    { value: "other", label: "Other" },
  ],
  continuation: [
    { value: "3m", label: "3M FVG" },
    { value: "5m", label: "5M FVG" },
    { value: "15m", label: "15M FVG" },
    { value: "other", label: "Other" },
  ],
};

const REACTION_TYPE_OPTIONS = [
  { value: "liquidity_sweep", label: "Liquidity Sweep" },
  { value: "unmitigated_fvg", label: "Unmitigated FVG" },
  { value: "continuation", label: "Continuation (no area — expect a move from the open)" },
  { value: "other", label: "Other" },
];

interface LevelSelectProps {
  label: string;
  typeValue: string | null | undefined;
  detailValue: string | null | undefined;
  onTypeChange: (v: string | null) => void;
  onDetailChange: (v: string | null) => void;
}

function LevelSelect({ label, typeValue, detailValue, onTypeChange, onDetailChange }: LevelSelectProps) {
  const detailOptions = typeValue ? LEVEL_DETAIL_OPTIONS[typeValue] ?? [] : [];
  return (
    <>
      <div>
        <label className={LABEL_CLASS}>{label}</label>
        <select
          className={SELECT_CLASS}
          value={typeValue ?? ""}
          onChange={(e) => {
            onTypeChange(e.target.value === "" ? null : e.target.value);
            onDetailChange(null);
          }}
        >
          <option value="">Select…</option>
          {LEVEL_TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>
      {typeValue && detailOptions.length > 0 && (
        <div className="ml-3 pl-3 border-l-2 border-border">
          <label className={LABEL_CLASS}>Detail</label>
          <select
            className={SELECT_CLASS}
            value={detailValue ?? ""}
            onChange={(e) => onDetailChange(e.target.value === "" ? null : e.target.value)}
          >
            <option value="">Select…</option>
            {detailOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      )}
    </>
  );
}

function emptyForm(): ScenarioCreateRequest {
  return {
    reaction_setup_type: null,
    reaction_setup_detail: null,
    target_level_type: null,
    target_level_detail: null,
    notes: "",
  };
}

function formFromScenario(scenario: PlanScenario): ScenarioCreateRequest {
  return {
    reaction_setup_type: scenario.reaction_setup_type,
    reaction_setup_detail: scenario.reaction_setup_detail,
    target_level_type: scenario.target_level_type,
    target_level_detail: scenario.target_level_detail,
    notes: scenario.notes,
  };
}

export function ScenarioForm({ onAdd, saving, editing, onSaveEdit, onCancelEdit }: ScenarioFormProps) {
  const isEditing = editing !== undefined;
  const [form, setForm] = useState<ScenarioCreateRequest>(
    () => (editing ? formFromScenario(editing) : emptyForm()),
  );
  const [justAdded, setJustAdded] = useState(false);

  function setField<K extends keyof ScenarioCreateRequest>(key: K, value: ScenarioCreateRequest[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setJustAdded(false);
  }

  function handleReactionTypeChange(value: string) {
    setField("reaction_setup_type", value === "" ? null : value);
    setField("reaction_setup_detail", null);
  }

  async function handleAdd() {
    if (isEditing) {
      await onSaveEdit?.(form);
      return;
    }
    await onAdd?.(form);
    setForm(emptyForm());
    setJustAdded(true);
  }

  const reactionDetailOptions = form.reaction_setup_type
    ? REACTION_DETAIL_OPTIONS[form.reaction_setup_type] ?? []
    : [];
  const isEmpty = !form.reaction_setup_type && !form.target_level_type && !form.notes;

  return (
    <div className="space-y-3">
      <div>
        <label className={LABEL_CLASS}>Reaction Area</label>
        <select
          className={SELECT_CLASS}
          value={form.reaction_setup_type ?? ""}
          onChange={(e) => handleReactionTypeChange(e.target.value)}
        >
          <option value="">Select…</option>
          {REACTION_TYPE_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>
      {form.reaction_setup_type && reactionDetailOptions.length > 0 && (
        <div className="ml-3 pl-3 border-l-2 border-border">
          <label className={LABEL_CLASS}>Detail</label>
          <select
            className={SELECT_CLASS}
            value={form.reaction_setup_detail ?? ""}
            onChange={(e) => setField("reaction_setup_detail", e.target.value === "" ? null : e.target.value)}
          >
            <option value="">Select…</option>
            {reactionDetailOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      )}

      <LevelSelect
        label="Target / Draw on Liquidity (DOL)"
        typeValue={form.target_level_type}
        detailValue={form.target_level_detail}
        onTypeChange={(v) => setField("target_level_type", v)}
        onDetailChange={(v) => setField("target_level_detail", v)}
      />

      <div>
        <label className={LABEL_CLASS}>Notes</label>
        <textarea
          value={form.notes ?? ""}
          onChange={(e) => setField("notes", e.target.value)}
          placeholder="anything else worth capturing about this scenario"
          rows={2}
          className="w-full bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-2 outline-none focus:border-bull resize-none placeholder:text-text-dim"
        />
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleAdd}
          disabled={saving || (isEmpty && !isEditing)}
          className="px-3 py-1.5 rounded text-xs font-semibold bg-bull text-[#0f0f0f] hover:opacity-90 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed transition-opacity"
        >
          {isEditing ? (saving ? "Saving…" : "Save Changes") : (saving ? "Adding…" : "Add Scenario")}
        </button>
        {isEditing && (
          <button
            type="button"
            onClick={onCancelEdit}
            disabled={saving}
            className="px-3 py-1.5 rounded text-xs text-text-muted hover:text-text-primary cursor-pointer transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
        )}
        {justAdded && <span className="text-[11px] text-text-muted">Added — add another or scroll down to review</span>}
      </div>
    </div>
  );
}
