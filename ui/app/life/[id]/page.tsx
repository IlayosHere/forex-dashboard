"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { LifeMoodPicker } from "@/components/LifeMoodPicker";
import { TagInput } from "@/components/TagInput";

import { useLifeEntry } from "@/lib/useLifeEntry";
import { updateLifeEntry, deleteLifeEntry } from "@/lib/api";
import type { LifeMood } from "@/lib/types";

interface Props {
  params: Promise<{ id: string }>;
}

export default function LifeEntryPage({ params }: Props) {
  const { id } = use(params);
  const router = useRouter();
  const { entry, loading, error } = useLifeEntry(id);

  const [body, setBody] = useState("");
  const [mood, setMood] = useState<LifeMood | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    if (!entry) return;
    setBody(entry.body);
    setMood(entry.mood);
    setTags([...entry.tags]);
  }, [entry]);

  async function handleSave() {
    if (!entry) return;
    setSaving(true);
    setSaveError(null);
    try {
      await updateLifeEntry(id, {
        body: body.trim() || undefined,
        mood: mood ?? undefined,
        clear_mood: mood === null && entry.mood !== null,
        tags,
      });
      router.back();
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : "Failed to save");
      setSaving(false);
    }
  }

  async function handleDelete() {
    setSaving(true);
    try {
      await deleteLifeEntry(id);
      router.back();
    } catch {
      setSaving(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void handleSave();
    }
  }

  if (loading) {
    return <p className="text-text-muted text-sm p-6">Loading…</p>;
  }
  if (error || !entry) {
    return <p className="text-[#ef5350] text-sm p-6">{error ?? "Entry not found"}</p>;
  }

  return (
    <div className="max-w-xl mx-auto px-4 py-6 space-y-4">
      <button
        onClick={() => router.back()}
        className="text-text-muted hover:text-text-primary text-sm cursor-pointer transition-colors"
      >
        ← Back
      </button>

      <div className="bg-surface-raised border border-border rounded-lg overflow-hidden focus-within:border-[#26a69a]/40 transition-colors">
        <div className="border-b border-border px-4 pt-3 pb-2">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={5}
            autoFocus
            className="w-full bg-transparent text-sm text-text-primary resize-none outline-none"
          />
        </div>
        <div className="px-3 py-2 space-y-2">
          <LifeMoodPicker value={mood} onChange={setMood} disabled={saving} />
          <TagInput tags={tags} onChange={setTags} />
          {saveError && <p className="text-[#ef5350] text-xs">{saveError}</p>}
          <div className="flex items-center justify-between">
            {confirmDelete ? (
              <div className="flex gap-2">
                <Button size="sm" variant="destructive" onClick={() => { void handleDelete(); }} disabled={saving}>
                  Confirm delete
                </Button>
                <Button size="sm" variant="outline" onClick={() => setConfirmDelete(false)}>
                  Cancel
                </Button>
              </div>
            ) : (
              <Button size="sm" variant="outline" onClick={() => setConfirmDelete(true)} disabled={saving}>
                Delete
              </Button>
            )}
            <Button size="sm" onClick={() => { void handleSave(); }} disabled={saving || !body.trim()}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
