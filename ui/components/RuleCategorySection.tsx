"use client";

import { useState, useEffect } from "react";

import { RuleCard } from "@/components/RuleCard";

import type { Rule } from "@/lib/types";

interface RuleCategorySectionProps {
  categoryName: string;
  rules: Rule[];
  onEdit: (rule: Rule) => void;
  onDelete: (id: string) => void;
}

const STORAGE_PREFIX = "rules_category_collapsed_";

function getStorageKey(name: string): string {
  return `${STORAGE_PREFIX}${name}`;
}

export function RuleCategorySection({
  categoryName,
  rules,
  onEdit,
  onDelete,
}: RuleCategorySectionProps) {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(getStorageKey(categoryName)) === "true";
  });

  useEffect(() => {
    localStorage.setItem(getStorageKey(categoryName), String(collapsed));
  }, [collapsed, categoryName]);

  const totalBreaks = rules.reduce((sum, r) => sum + r.break_count, 0);

  return (
    <div className="mb-4">
      <button
        type="button"
        onClick={() => setCollapsed((prev) => !prev)}
        className="w-full flex items-center gap-2 px-1 py-2 text-left group"
        aria-expanded={!collapsed}
      >
        <span
          className={`text-muted-foreground text-xs transition-transform duration-200 ${
            collapsed ? "" : "rotate-90"
          }`}
          aria-hidden="true"
        >
          ▶
        </span>
        <span className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
          {categoryName}
        </span>
        <span className="text-xs text-[#555555]">
          ({rules.length} {rules.length === 1 ? "rule" : "rules"} · {totalBreaks} {totalBreaks === 1 ? "break" : "breaks"})
        </span>
      </button>

      {!collapsed && (
        <div className="border border-border rounded overflow-hidden bg-card">
          {rules.map((rule) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}
    </div>
  );
}
