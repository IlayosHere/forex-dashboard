"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { MistakeList } from "@/components/MistakeList";
import { MistakeReviewPanel } from "@/components/MistakeReviewPanel";

import { createMistake, deleteMistake, incrementMistake } from "@/lib/api";
import { useMistakes } from "@/lib/useMistakes";
import { useRules } from "@/lib/useRules";
import { useShowMoney } from "@/lib/useShowMoney";

const JOURNAL_TABS = [
  { label: "Trades", href: "/journal" },
  { label: "Calendar", href: "/journal/calendar" },
  { label: "Mistakes", href: "/journal/mistakes" },
  { label: "Rules", href: "/journal/rules" },
];

type MistakesView = "log" | "review";

export default function MistakesPage() {
  const pathname = usePathname();
  const [draft, setDraft] = useState("");
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [view, setView] = useState<MistakesView>("log");

  const { mistakes, loading, error, refetch } = useMistakes();
  const { rules } = useRules();
  const [showMoney] = useShowMoney();

  const rulesMap = useMemo(() => {
    const map = new Map<string, string[]>();
    rules.forEach((rule) => {
      rule.linked_mistakes.forEach((m) => {
        const existing = map.get(m.id) ?? [];
        map.set(m.id, [...existing, rule.title]);
      });
    });
    return map;
  }, [rules]);

  async function handleAdd(): Promise<void> {
    const name = draft.trim();
    if (!name) return;
    try {
      await createMistake(name);
      setDraft("");
      setMutationError(null);
      refetch();
    } catch (e) {
      setMutationError(e instanceof Error ? e.message : "Failed to add mistake");
    }
  }

  async function handleIncrement(id: string): Promise<void> {
    try {
      await incrementMistake(id);
      setMutationError(null);
      refetch();
    } catch (e) {
      setMutationError(e instanceof Error ? e.message : "Failed to update mistake");
    }
  }

  async function handleDelete(id: string): Promise<void> {
    try {
      await deleteMistake(id);
      setMutationError(null);
      refetch();
    } catch (e) {
      setMutationError(e instanceof Error ? e.message : "Failed to delete mistake");
    }
  }

  const displayError = mutationError ?? error;

  return (
    <div className="p-6">
      {/* Back link */}
      <Link
        href="/"
        className="text-xs text-[#777777] hover:text-[#e0e0e0] transition-colors inline-flex items-center gap-1 mb-3"
      >
        ← Dashboard
      </Link>

      {/* Page header */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-[#e0e0e0]">Journal</h1>
        <div className="flex h-7 rounded border border-border bg-surface-input p-0.5 gap-0.5">
          {(["log", "review"] as const).map((v) => (
            <button
              key={v}
              type="button"
              onClick={() => setView(v)}
              className={`px-3 rounded-sm text-xs font-medium transition-colors cursor-pointer ${
                view === v
                  ? "bg-bull/20 text-bull ring-1 ring-inset ring-bull/40"
                  : "text-text-dim hover:text-text-muted"
              }`}
            >
              {v === "log" ? "Log" : "Review"}
            </button>
          ))}
        </div>
      </div>

      {/* Journal tab nav */}
      <div className="flex gap-2 mb-4">
        {JOURNAL_TABS.map((tab) => {
          const isActive = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                isActive
                  ? "border-[#26a69a] text-[#26a69a] bg-[#26a69a]/10"
                  : "border-[#2a2a2a] text-[#777] hover:text-[#e0e0e0]"
              }`}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>

      {view === "review" ? (
        <MistakeReviewPanel showMoney={showMoney} />
      ) : (
        <>
          {/* Input row */}
          <div className="flex gap-2 mb-6">
            <Input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") void handleAdd(); }}
              placeholder="Log a new mistake..."
              className="flex-1 h-9 text-sm"
            />
            <Button
              onClick={() => void handleAdd()}
              disabled={draft.trim().length === 0}
              className="h-9 px-4 text-sm shrink-0"
            >
              + Add
            </Button>
          </div>

          {/* Error display */}
          {displayError && (
            <p className="text-xs text-bear mb-4">{displayError}</p>
          )}

          {/* Loading state */}
          {loading ? (
            <p className="text-sm text-muted-foreground py-8 text-center">Loading...</p>
          ) : (
            <MistakeList
              mistakes={mistakes}
              onIncrement={(id) => void handleIncrement(id)}
              onDelete={(id) => void handleDelete(id)}
              rulesMap={rulesMap}
            />
          )}
        </>
      )}
    </div>
  );
}
