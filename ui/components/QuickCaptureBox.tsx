"use client";

import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";

import { LifeMoodPicker } from "@/components/LifeMoodPicker";
import { TagInput } from "@/components/TagInput";

import { createLifeEntry } from "@/lib/api";
import type { LifeEntry, LifeMood } from "@/lib/types";

interface QuickCaptureBoxProps {
  onCreated: (entry: LifeEntry) => void;
  knownTags?: string[];
  onTagsChanged?: () => void;
}

export function QuickCaptureBox({ onCreated, knownTags, onTagsChanged }: QuickCaptureBoxProps) {
  const [body, setBody] = useState("");
  const [mood, setMood] = useState<LifeMood | null>(null);
  const [tags, setTags] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  async function handleSave() {
    const trimmed = body.trim();
    if (!trimmed) return;
    setSaving(true);
    setError(null);
    try {
      const entry = await createLifeEntry({ body: trimmed, mood, tags });
      onCreated(entry);
      onTagsChanged?.();
      setBody("");
      setMood(null);
      setTags([]);
      textareaRef.current?.focus();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      void handleSave();
    }
  }

  const hasBody = body.length > 0;

  return (
    <div className="bg-surface-raised border border-border rounded-lg overflow-hidden focus-within:border-[#26a69a]/40 transition-colors">
      <div className="border-b border-border px-4 pt-3 pb-2">
        <textarea
          ref={textareaRef}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="What's on your mind? (Cmd+Enter to save)"
          rows={3}
          autoFocus
          className="w-full bg-transparent text-text-primary text-sm resize-none outline-none placeholder:text-text-muted"
        />
      </div>
      <div className="px-3 py-2 space-y-2">
        <div
          className={`space-y-2 overflow-hidden transition-all duration-200 ${
            hasBody ? "opacity-100 max-h-40" : "opacity-0 max-h-0"
          }`}
        >
          <LifeMoodPicker value={mood} onChange={setMood} disabled={saving} />
          <TagInput tags={tags} onChange={setTags} suggestions={knownTags} />
        </div>
        {error && <p className="text-[#ef5350] text-xs">{error}</p>}
        <div className="flex justify-end">
          <Button
            size="sm"
            onClick={() => { void handleSave(); }}
            disabled={saving || !body.trim()}
          >
            {saving ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>
    </div>
  );
}
