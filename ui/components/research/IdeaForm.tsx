"use client";

import { useState } from "react";

import { createQueueItem } from "@/lib/researchApi";
import type { QueueKind, QueueStage, ResearchIdea } from "@/lib/researchTypes";

interface IdeaFormProps {
  ideas: ResearchIdea[];
  onSaved: () => void;
}

const FIELD = "w-full rounded border border-border bg-surface-input px-3 py-2 text-sm text-text-primary placeholder:text-text-dim";

export function IdeaForm({ ideas, onSaved }: IdeaFormProps) {
  const [kind, setKind] = useState<QueueKind>("idea");
  const [title, setTitle] = useState("");
  const [stage, setStage] = useState<QueueStage>("any");
  const [about, setAbout] = useState("");
  const [body, setBody] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const ready = title.trim().length >= 3 && body.trim().length >= 10 && (kind === "idea" || about !== "");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      await createQueueItem({ kind, title: title.trim(), stage, about: kind === "note" ? about : null, body: body.trim() });
      setTitle("");
      setBody("");
      setAbout("");
      setSaved(true);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="max-w-2xl space-y-4 rounded-lg border border-border bg-surface-raised p-4">
      <div role="radiogroup" aria-label="What are you adding" className="flex gap-2">
        {(["idea", "note"] as QueueKind[]).map((k) => (
          <button
            key={k}
            type="button"
            role="radio"
            aria-checked={kind === k}
            onClick={() => setKind(k)}
            className={`rounded-full border px-3 py-1 text-xs ${kind === k ? "border-border-light bg-elevated text-text-primary" : "border-border text-text-muted"}`}
          >
            {k === "idea" ? "A new idea" : "A note on a tested idea"}
          </button>
        ))}
      </div>

      <label className="block text-xs text-text-muted">
        Title
        <input className={`${FIELD} mt-1`} value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} placeholder="Short name for the idea" />
      </label>

      <div className="flex flex-wrap gap-4">
        <label className="text-xs text-text-muted">
          Stage
          <select className={`${FIELD} mt-1`} value={stage} onChange={(e) => setStage(e.target.value as QueueStage)}>
            <option value="any">Any stage</option>
            <option value="1">Stage 1</option>
            <option value="2">Stage 2</option>
            <option value="3">Stage 3</option>
          </select>
        </label>
        {kind === "note" && (
          <label className="min-w-[14rem] flex-1 text-xs text-text-muted">
            Which idea is it about
            <select className={`${FIELD} mt-1`} value={about} onChange={(e) => setAbout(e.target.value)}>
              <option value="">Choose one</option>
              {ideas.map((i) => (
                <option key={i.id} value={i.id}>{i.name} ({i.id})</option>
              ))}
            </select>
          </label>
        )}
      </div>

      <label className="block text-xs text-text-muted">
        In your own words
        <textarea className={`${FIELD} mt-1 min-h-32`} value={body} maxLength={4000} onChange={(e) => setBody(e.target.value)}
          placeholder="What do you think price does, and who has to trade that way? If you have a rule, write it down: when, which direction, how it exits." />
      </label>

      <p className="text-xs leading-relaxed text-text-dim">
        This is saved as a file in the research repo. It is read at the start of the next round and checked against the idea list first, so a repeat is answered, not retested.
      </p>

      <div className="flex items-center gap-3">
        <button type="submit" disabled={!ready || saving}
          className="rounded bg-elevated px-4 py-2 text-sm text-text-primary hover:bg-surface-raised disabled:opacity-40 border border-border-light">
          {saving ? "Saving..." : "Add to the queue"}
        </button>
        {saved && <span className="text-xs text-bull">Saved. It is in the queue for the next round.</span>}
        {error && <span role="alert" className="text-xs text-bear">{error}</span>}
      </div>
    </form>
  );
}
