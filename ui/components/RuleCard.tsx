"use client";

import { useState } from "react";

import type { Rule } from "@/lib/types";

interface RuleCardProps {
  rule: Rule;
  onEdit: (rule: Rule) => void;
  onDelete: (id: string) => void;
}

const BREAK_HIGH = 10;
const BREAK_MED = 4;

function breakBadge(count: number): string {
  if (count === 0) return "text-[#555555]";
  if (count <= 3) return "text-[#e0e0e0]";
  if (count < BREAK_HIGH) return "text-amber-400 bg-amber-950/40 border border-amber-900/50 rounded px-1.5";
  return "text-[#ef5350] bg-red-950/40 border border-red-900/50 rounded px-1.5";
}

export function RuleCard({ rule, onEdit, onDelete }: RuleCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const badgeClass = breakBadge(rule.break_count);

  if (confirmDelete) {
    return (
      <div className="flex items-center gap-3 px-4 py-3 bg-card border-b border-border">
        <span className="flex-1 text-sm text-muted-foreground">
          Delete &quot;{rule.title}&quot;?
        </span>
        <button
          type="button"
          onClick={() => { onDelete(rule.id); setConfirmDelete(false); }}
          className="text-xs text-[#ef5350] px-2"
        >
          Yes
        </button>
        <button
          type="button"
          onClick={() => setConfirmDelete(false)}
          className="text-xs text-muted-foreground px-2"
        >
          No
        </button>
      </div>
    );
  }

  return (
    <div className="border-b border-border last:border-b-0">
      <button
        type="button"
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-elevated transition-colors text-left"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
      >
        <span className="flex-1 text-sm text-foreground truncate">{rule.title}</span>
        {rule.category && (
          <span className="text-xs text-muted-foreground uppercase shrink-0 hidden sm:block">
            {rule.category.name}
          </span>
        )}
        <span className={`text-xs font-mono tabular-nums shrink-0 ${badgeClass}`}>
          {rule.break_count > 0 ? `×${rule.break_count}` : "×0"}
        </span>
        <span
          className={`text-muted-foreground shrink-0 transition-transform duration-200 ${
            expanded ? "rotate-180" : ""
          }`}
          aria-hidden="true"
        >
          ▾
        </span>
      </button>

      {expanded && (
        <div className="px-4 pb-3 space-y-2">
          {rule.body && (
            <p className="text-sm text-[#9e9e9e] line-clamp-3">{rule.body}</p>
          )}
          {rule.linked_mistakes.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {rule.linked_mistakes.map((m) => (
                <span
                  key={m.id}
                  className="inline-flex items-center bg-[#1e1e1e] text-[#9e9e9e] text-xs rounded-full px-2.5 py-1"
                >
                  {m.name}
                </span>
              ))}
            </div>
          )}
          <div className="flex items-center gap-3 pt-1">
            <button
              type="button"
              onClick={() => onEdit(rule)}
              className="text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Edit
            </button>
            <button
              type="button"
              onClick={() => setConfirmDelete(true)}
              className="text-xs text-[#ef5350]/70 hover:text-[#ef5350] transition-colors"
            >
              Delete
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
