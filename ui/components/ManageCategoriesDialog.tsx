"use client";

import { useState } from "react";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

import type { Rule, RuleCategory } from "@/lib/types";

interface ManageCategoriesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  categories: RuleCategory[];
  rules: Rule[];
  onRename: (id: string, name: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

interface RowState {
  editingId: string | null;
  editValue: string;
  confirmDeleteId: string | null;
}

const INITIAL_ROW: RowState = { editingId: null, editValue: "", confirmDeleteId: null };

export function ManageCategoriesDialog({
  open,
  onOpenChange,
  categories,
  rules,
  onRename,
  onDelete,
}: ManageCategoriesDialogProps) {
  const [row, setRow] = useState<RowState>(INITIAL_ROW);

  function ruleCount(categoryId: string): number {
    return rules.filter((r) => r.category?.id === categoryId).length;
  }

  function startEdit(cat: RuleCategory) {
    setRow({ editingId: cat.id, editValue: cat.name, confirmDeleteId: null });
  }

  function cancelEdit() {
    setRow(INITIAL_ROW);
  }

  async function commitEdit(id: string) {
    const name = row.editValue.trim();
    if (!name) return;
    await onRename(id, name);
    setRow(INITIAL_ROW);
  }

  function startDelete(id: string) {
    setRow({ editingId: null, editValue: "", confirmDeleteId: id });
  }

  async function commitDelete(id: string) {
    await onDelete(id);
    setRow(INITIAL_ROW);
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-[360px]">
        <SheetHeader>
          <SheetTitle>Manage Categories</SheetTitle>
        </SheetHeader>

        <div className="px-4 py-4 space-y-1">
          {categories.length === 0 && (
            <p className="text-sm text-muted-foreground py-8 text-center">No categories yet.</p>
          )}

          {categories.map((cat) => {
            const count = ruleCount(cat.id);

            if (row.editingId === cat.id) {
              return (
                <div key={cat.id} className="flex items-center gap-2 py-2">
                  <input
                    autoFocus
                    value={row.editValue}
                    onChange={(e) => setRow((s) => ({ ...s, editValue: e.target.value }))}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") void commitEdit(cat.id);
                      if (e.key === "Escape") cancelEdit();
                    }}
                    className="flex-1 bg-[#1a1a1a] border border-[#26a69a] text-sm text-[#e0e0e0] rounded px-2 py-1 outline-none"
                  />
                  <button type="button" onClick={() => void commitEdit(cat.id)} className="text-xs text-[#26a69a] px-1">
                    Save
                  </button>
                  <button type="button" onClick={cancelEdit} className="text-xs text-muted-foreground px-1">
                    Esc
                  </button>
                </div>
              );
            }

            if (row.confirmDeleteId === cat.id) {
              return (
                <div key={cat.id} className="flex items-center gap-2 py-2">
                  <span className="flex-1 text-xs text-muted-foreground">
                    {count > 0
                      ? `${count} ${count === 1 ? "rule" : "rules"} will be uncategorized. Delete anyway?`
                      : `Delete "${cat.name}"?`}
                  </span>
                  <button type="button" onClick={() => void commitDelete(cat.id)} className="text-xs text-[#ef5350] px-1">
                    Yes
                  </button>
                  <button type="button" onClick={() => setRow(INITIAL_ROW)} className="text-xs text-muted-foreground px-1">
                    No
                  </button>
                </div>
              );
            }

            return (
              <div key={cat.id} className="flex items-center gap-2 py-2 group">
                <span className="flex-1 text-sm text-foreground">{cat.name}</span>
                <span className="text-xs text-muted-foreground">({count})</span>
                <button
                  type="button"
                  onClick={() => startEdit(cat)}
                  aria-label={`Rename ${cat.name}`}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100 px-1"
                >
                  ✎
                </button>
                <button
                  type="button"
                  onClick={() => startDelete(cat.id)}
                  aria-label={`Delete ${cat.name}`}
                  className="text-xs text-muted-foreground hover:text-[#ef5350] transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100 px-1"
                >
                  ×
                </button>
              </div>
            );
          })}
        </div>
      </SheetContent>
    </Sheet>
  );
}
