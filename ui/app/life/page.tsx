"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { LifeTimeline } from "@/components/LifeTimeline";
import { QuickCaptureBox } from "@/components/QuickCaptureBox";

import { useLifeEntries } from "@/lib/useLifeEntries";
import { useLifeTags } from "@/lib/useLifeTags";
import type { LifeEntry } from "@/lib/types";

export default function LifePage() {
  const [activeTag, setActiveTag] = useState<string | null>(null);
  const { entries, loading, error, refetch } = useLifeEntries({
    limit: 100,
    tag: activeTag ?? undefined,
  });
  const [optimistic, setOptimistic] = useState<LifeEntry[]>([]);
  const { tags: knownTags, reload: reloadTags } = useLifeTags();

  const handleCreated = useCallback((entry: LifeEntry) => {
    setOptimistic((prev) => [entry, ...prev]);
  }, []);

  const handleTagClick = useCallback((tag: string) => {
    setActiveTag((prev) => (prev === tag ? null : tag));
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && activeTag) setActiveTag(null);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [activeTag]);

  // optimistic entries always show regardless of active filter (UX: never hide after save)
  const merged = [
    ...optimistic.filter((o) => !entries.some((e) => e.id === o.id)),
    ...entries,
  ];

  return (
    <div className="max-w-2xl mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold text-text-primary">Life Journal</h1>
        <Link
          href="/life/calendar"
          className="text-sm text-text-muted hover:text-text-primary transition-colors"
        >
          Calendar →
        </Link>
      </div>

      <QuickCaptureBox
        onCreated={handleCreated}
        knownTags={knownTags}
        onTagsChanged={reloadTags}
      />

      {activeTag && (
        <div className="flex items-center gap-3 -mt-2">
          <button
            type="button"
            onClick={() => setActiveTag(null)}
            className="inline-flex items-center gap-1 bg-[#26a69a]/15 border border-[#26a69a]/50 text-[#26a69a] text-[10px] rounded-full px-2.5 py-1 cursor-pointer transition-all duration-150"
          >
            {activeTag}
            <span className="ml-0.5 text-[11px] leading-none">×</span>
          </button>
          <p className="text-[10px] text-text-muted">
            {merged.length} {merged.length === 1 ? "entry" : "entries"}
            {" · "}
            <button
              type="button"
              onClick={() => setActiveTag(null)}
              className="underline underline-offset-2 hover:text-text-primary transition-colors cursor-pointer"
            >
              clear
            </button>
          </p>
        </div>
      )}

      {error && (
        <div className="rounded bg-[#ef5350]/10 border border-[#ef5350]/30 px-3 py-2 text-sm text-[#ef5350]">
          {error}
          <button onClick={refetch} className="ml-2 underline text-xs cursor-pointer">
            Retry
          </button>
        </div>
      )}

      {loading && merged.length === 0 ? (
        <p className="text-text-muted text-sm text-center py-8">Loading…</p>
      ) : (
        <LifeTimeline entries={merged} activeTag={activeTag ?? undefined} onTagClick={handleTagClick} />
      )}
    </div>
  );
}
