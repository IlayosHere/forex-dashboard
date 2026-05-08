"use client";

import { useEffect, useState } from "react";

import { FeelingPicker } from "@/components/FeelingPicker";

import type { SessionUpsertRequest, TradingFeeling, TradingSession } from "@/lib/types";

const LABEL_CLASS = "text-[10px] uppercase tracking-widest text-text-muted w-16 shrink-0 pt-1";

const PLAN_OPTIONS: { value: boolean; label: string; activeColor: string }[] = [
  { value: true,  label: "Yes — I have a setup in mind", activeColor: "#26a69a" },
  { value: false, label: "No — nothing to trade today",  activeColor: "#777777" },
];

interface SessionJournalPanelProps {
  session: TradingSession | null;
  saving: boolean;
  onSave: (data: SessionUpsertRequest) => Promise<void>;
  onSaved?: () => void;
}

function buildInitialState(session: TradingSession | null): SessionUpsertRequest {
  return {
    had_pre_session_plan: session?.had_pre_session_plan ?? null,
    feeling_pre:    (session?.feeling_pre    as TradingFeeling | null) ?? null,
    feeling_during: (session?.feeling_during as TradingFeeling | null) ?? null,
    feeling_post:   (session?.feeling_post   as TradingFeeling | null) ?? null,
    session_notes:  session?.session_notes ?? "",
  };
}

export function SessionJournalPanel({ session, saving, onSave, onSaved }: SessionJournalPanelProps) {
  const [draft, setDraft] = useState<SessionUpsertRequest>(() => buildInitialState(session));
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (session !== null) {
      setDraft(buildInitialState(session));
      setSaved(false);
    }
  }, [session]);

  function setField<K extends keyof SessionUpsertRequest>(key: K, value: SessionUpsertRequest[K]) {
    setDraft((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  async function handleSave() {
    await onSave(draft);
    setSaved(true);
    onSaved?.();
  }

  return (
    <div className="border border-border rounded-lg p-4 bg-card mb-4">
      <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3">
        Session Journal
      </h3>

      {/* Pre-session plan */}
      <div className="flex gap-3 items-start mb-3">
        <span className={LABEL_CLASS}>Plan</span>
        <div className="flex flex-wrap gap-1.5">
          {PLAN_OPTIONS.map((opt) => {
            const isActive = draft.had_pre_session_plan === opt.value;
            return (
              <button
                key={String(opt.value)}
                type="button"
                onClick={() => setField("had_pre_session_plan", isActive ? null : opt.value)}
                className={`px-2 py-1 rounded text-[11px] font-medium border transition-colors cursor-pointer ${
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

      {/* Feelings rows */}
      <div className="flex flex-col gap-3 mb-3">
        <div className="flex gap-3 items-start">
          <span className={LABEL_CLASS}>Pre</span>
          <FeelingPicker value={draft.feeling_pre} onChange={(v) => setField("feeling_pre", v)} />
        </div>
        <div className="flex gap-3 items-start">
          <span className={LABEL_CLASS}>During</span>
          <FeelingPicker value={draft.feeling_during} onChange={(v) => setField("feeling_during", v)} />
        </div>
        <div className="flex gap-3 items-start">
          <span className={LABEL_CLASS}>Post</span>
          <FeelingPicker value={draft.feeling_post} onChange={(v) => setField("feeling_post", v)} />
        </div>
      </div>

      {/* Notes */}
      <textarea
        value={draft.session_notes}
        onChange={(e) => setField("session_notes", e.target.value)}
        placeholder="Session notes…"
        rows={2}
        className="w-full bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-2 outline-none focus:border-bull resize-none mb-3 placeholder:text-text-dim"
      />

      {/* Save */}
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="px-3 py-1.5 rounded text-xs font-semibold bg-bull text-[#0f0f0f] hover:opacity-90 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed transition-opacity"
        >
          {saving ? "Saving…" : "Save Session"}
        </button>
        {saved && <span className="text-[11px] text-text-muted">Saved</span>}
      </div>
    </div>
  );
}
