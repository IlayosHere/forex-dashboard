"use client";

import { useState } from "react";

import { FeelingPicker } from "@/components/FeelingPicker";

import type { Checkpoint, TradingFeeling, TradingSession } from "@/lib/types";

interface DuringSectionProps {
  session: TradingSession | null;
  sessionSaving: boolean;
  onFeelingChange: (value: TradingFeeling | null) => void;
  checkpoints: Checkpoint[];
  checkpointSaving: boolean;
  onAddCheckpoint: (note: string) => Promise<void>;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function DuringSection({
  session, sessionSaving, onFeelingChange, checkpoints, checkpointSaving, onAddCheckpoint,
}: DuringSectionProps) {
  const [note, setNote] = useState("");

  async function handleAdd() {
    if (!note.trim()) return;
    await onAddCheckpoint(note.trim());
    setNote("");
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs text-text-muted mb-1">How are you feeling right now?</label>
        <FeelingPicker
          value={session?.feeling_during ?? null}
          onChange={onFeelingChange}
          disabled={sessionSaving}
        />
      </div>

      <div>
        <label className="block text-xs text-text-muted mb-1">Quick note</label>
        <div className="flex gap-2">
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") void handleAdd(); }}
            placeholder="swept asia low, watching for reaction…"
            className="flex-1 bg-surface-input border border-border text-sm text-text-primary rounded px-3 py-1.5 outline-none focus:border-bull placeholder:text-text-dim"
          />
          <button
            type="button"
            onClick={handleAdd}
            disabled={checkpointSaving || !note.trim()}
            className="px-3 py-1.5 rounded text-xs font-semibold bg-bull text-[#0f0f0f] hover:opacity-90 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed transition-opacity"
          >
            Add
          </button>
        </div>
      </div>

      {checkpoints.length > 0 && (
        <div className="space-y-1.5">
          {checkpoints.map((cp, i) => (
            <div key={i} className="flex gap-2 text-xs">
              <span className="text-text-dim tabular-nums shrink-0">{formatTime(cp.timestamp)}</span>
              <span className="text-text-primary">{cp.note}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
