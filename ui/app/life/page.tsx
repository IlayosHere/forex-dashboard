"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import { LifeTimeline } from "@/components/LifeTimeline";
import { QuickCaptureBox } from "@/components/QuickCaptureBox";

import { useLifeEntries } from "@/lib/useLifeEntries";
import type { LifeEntry } from "@/lib/types";

export default function LifePage() {
  const { entries, loading, error, refetch } = useLifeEntries({ limit: 100 });
  const [optimistic, setOptimistic] = useState<LifeEntry[]>([]);

  const handleCreated = useCallback((entry: LifeEntry) => {
    setOptimistic((prev) => [entry, ...prev]);
  }, []);

  const merged = [
    ...entries,
    ...optimistic.filter((o) => !entries.some((e) => e.id === o.id)),
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

      <QuickCaptureBox onCreated={handleCreated} />

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
        <LifeTimeline entries={merged} />
      )}
    </div>
  );
}
