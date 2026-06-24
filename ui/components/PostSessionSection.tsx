"use client";

import { useEffect, useState } from "react";

import { FeelingPicker } from "@/components/FeelingPicker";

import type { ExecutionGrade, PlanReview, TradingFeeling, TradingSession } from "@/lib/types";

interface PostSessionSectionProps {
  session: TradingSession | null;
  sessionSaving: boolean;
  onFeelingChange: (value: TradingFeeling | null) => void;
  onNotesSave: (notes: string) => void;
  review: PlanReview | null;
  reviewSaving: boolean;
  onSetExecutionGrade: (grade: ExecutionGrade | null) => void;
}

const GRADE_OPTIONS: { value: ExecutionGrade; label: string; activeColor: string }[] = [
  { value: "yes", label: "Yes", activeColor: "#26a69a" },
  { value: "mostly", label: "Mostly", activeColor: "#d4a017" },
  { value: "no", label: "No", activeColor: "#ef5350" },
];

export function PostSessionSection({
  session, sessionSaving, onFeelingChange, onNotesSave, review, reviewSaving, onSetExecutionGrade,
}: PostSessionSectionProps) {
  const [notes, setNotes] = useState(session?.session_notes ?? "");
  const [justSaved, setJustSaved] = useState(false);

  useEffect(() => {
    setNotes(session?.session_notes ?? "");
  }, [session?.session_notes]);

  function handleNotesBlur() {
    onNotesSave(notes);
    setJustSaved(true);
    setTimeout(() => setJustSaved(false), 1500);
  }

  const grade = review?.execution_grade ?? null;

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs text-text-muted mb-1">Followed your plan?</label>
        <div className="flex gap-1.5">
          {GRADE_OPTIONS.map((opt) => {
            const isActive = grade === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => onSetExecutionGrade(isActive ? null : opt.value)}
                disabled={reviewSaving}
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

      <div>
        <label className="block text-xs text-text-muted mb-1">How do you feel now?</label>
        <FeelingPicker
          value={session?.feeling_post ?? null}
          onChange={onFeelingChange}
          disabled={sessionSaving}
          compact
        />
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="block text-xs text-text-muted">Notes</label>
          {justSaved && <span className="text-[10px] text-text-dim">Saved</span>}
        </div>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          onBlur={handleNotesBlur}
          placeholder="how did the day go overall?"
          rows={3}
          className="w-full bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-2 outline-none focus:border-bull resize-none placeholder:text-text-dim"
        />
      </div>
    </div>
  );
}
