"use client";

import { useState, useEffect, useCallback } from "react";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { LinkedMistakesSelect } from "@/components/LinkedMistakesSelect";

import type { Rule, RuleCategory, LinkedMistake, Mistake } from "@/lib/types";
import { createRuleCategory } from "@/lib/api";

const TITLE_MAX = 80;

interface RuleSheetProps {
  rule: Rule | null;
  categories: RuleCategory[];
  mistakes: Mistake[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: RuleFormData) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
  onCategoryCreated: (cat: RuleCategory) => void;
}

export interface RuleFormData {
  title: string;
  body: string;
  categoryId: string | null;
  linkedMistakeIds: string[];
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function RuleSheet({
  rule,
  categories,
  mistakes,
  open,
  onOpenChange,
  onSave,
  onDelete,
  onCategoryCreated,
}: RuleSheetProps) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [catQuery, setCatQuery] = useState("");
  const [catOpen, setCatOpen] = useState(false);
  const [linkedMistakes, setLinkedMistakes] = useState<LinkedMistake[]>([]);
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const reset = useCallback(() => {
    setTitle(rule?.title ?? "");
    setBody(rule?.body ?? "");
    setCategoryId(rule?.category?.id ?? null);
    setCatQuery(rule?.category?.name ?? "");
    setLinkedMistakes(rule?.linked_mistakes ?? []);
    setSaving(false);
    setConfirmDelete(false);
  }, [rule]);

  useEffect(() => {
    if (open) reset();
  }, [open, reset]);

  const selectedCategory = categories.find((c) => c.id === categoryId);
  const filteredCats = categories.filter((c) =>
    c.name.toLowerCase().includes(catQuery.toLowerCase())
  );
  const showCreate = catQuery.trim().length > 0 &&
    !categories.some((c) => c.name.toLowerCase() === catQuery.trim().toLowerCase());

  async function handleSelectCategory(cat: RuleCategory) {
    setCategoryId(cat.id);
    setCatQuery(cat.name);
    setCatOpen(false);
  }

  async function handleCreateCategory() {
    const name = catQuery.trim();
    if (!name) return;
    try {
      const created = await createRuleCategory(name);
      onCategoryCreated(created);
      setCategoryId(created.id);
      setCatQuery(created.name);
      setCatOpen(false);
    } catch {
      // swallow — user can retry
    }
  }

  async function handleSave() {
    if (!title.trim()) return;
    setSaving(true);
    try {
      await onSave({
        title: title.trim(),
        body: body.trim(),
        categoryId,
        linkedMistakeIds: linkedMistakes.map((m) => m.id),
      });
      onOpenChange(false);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!rule || !onDelete) return;
    setSaving(true);
    try {
      await onDelete(rule.id);
      onOpenChange(false);
    } finally {
      setSaving(false);
    }
  }

  const titleOver = title.length > TITLE_MAX;
  const canSave = title.trim().length > 0 && !titleOver && !saving;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="flex flex-col w-[440px]">
        <SheetHeader>
          <SheetTitle>{rule ? "Edit Rule" : "Add Rule"}</SheetTitle>
        </SheetHeader>

        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Title *</label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={120}
              className="text-sm"
              placeholder="Rule title..."
            />
            <p className={`text-right text-xs mt-0.5 ${titleOver ? "text-[#ef5350]" : "text-[#555555]"}`}>
              {title.length} / {TITLE_MAX}
            </p>
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Category</label>
            {selectedCategory ? (
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-1 bg-[#1e1e1e] text-[#e0e0e0] text-xs rounded-full px-2.5 py-1">
                  {selectedCategory.name}
                  <button
                    type="button"
                    onClick={() => { setCategoryId(null); setCatQuery(""); }}
                    className="text-[#777777] hover:text-[#ef5350] ml-0.5 transition-colors"
                    aria-label="Clear category"
                  >
                    ×
                  </button>
                </span>
              </div>
            ) : (
              <div className="relative">
                <input
                  value={catQuery}
                  onChange={(e) => { setCatQuery(e.target.value); setCatOpen(true); }}
                  onFocus={() => setCatOpen(true)}
                  onBlur={() => setTimeout(() => setCatOpen(false), 150)}
                  placeholder="Search or create category..."
                  className="w-full bg-[#1a1a1a] border border-[#2a2a2a] text-sm text-[#e0e0e0] rounded px-3 py-1.5 outline-none focus:border-[#26a69a] placeholder:text-[#555555]"
                />
                {catOpen && (filteredCats.length > 0 || showCreate) && (
                  <div className="absolute top-full left-0 right-0 mt-1 bg-[#1e1e1e] border border-[#2a2a2a] rounded py-1 z-20 max-h-40 overflow-y-auto">
                    {filteredCats.map((c) => (
                      <button
                        key={c.id}
                        type="button"
                        onMouseDown={(e) => { e.preventDefault(); void handleSelectCategory(c); }}
                        className="block w-full text-left px-3 py-1.5 text-xs text-[#e0e0e0] hover:bg-[#2a2a2a] transition-colors"
                      >
                        {c.name}
                      </button>
                    ))}
                    {showCreate && (
                      <button
                        type="button"
                        onMouseDown={(e) => { e.preventDefault(); void handleCreateCategory(); }}
                        className="block w-full text-left px-3 py-1.5 text-xs text-[#26a69a] hover:bg-[#2a2a2a] transition-colors"
                      >
                        + Create &quot;{catQuery.trim()}&quot;
                      </button>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Body / Reasoning</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={4}
              className="bg-[#1a1a1a] border border-[#2a2a2a] text-sm text-[#e0e0e0] rounded p-2 w-full resize-none outline-none focus:border-[#26a69a] placeholder:text-[#555555]"
              placeholder="Why this rule exists..."
            />
          </div>

          <div>
            <label className="text-xs text-muted-foreground mb-1 block">Linked Mistakes</label>
            <LinkedMistakesSelect
              selected={linkedMistakes}
              available={mistakes}
              onChange={setLinkedMistakes}
            />
          </div>

          {rule && (
            <p className="text-xs text-[#555555]">
              Broken {rule.break_count} {rule.break_count === 1 ? "time" : "times"} · Created {formatDate(rule.created_at)}
            </p>
          )}
        </div>

        <div className="px-4 py-3 border-t border-[#2a2a2a] flex items-center gap-2">
          {rule && onDelete && !confirmDelete && (
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="text-sm text-[#ef5350] hover:text-[#ef5350]/80 transition-colors cursor-pointer"
            >
              Delete
            </button>
          )}
          {confirmDelete && (
            <>
              <span className="text-xs text-muted-foreground">Confirm delete?</span>
              <button type="button" onClick={() => void handleDelete()} className="text-xs text-[#ef5350] px-2">Yes</button>
              <button type="button" onClick={() => setConfirmDelete(false)} className="text-xs text-muted-foreground px-2">No</button>
            </>
          )}
          <div className="flex-1" />
          <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button size="sm" disabled={!canSave} onClick={() => void handleSave()}>
            Save
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}
