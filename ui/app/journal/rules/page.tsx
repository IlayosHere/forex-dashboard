"use client";

import { useState, useMemo, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Button } from "@/components/ui/button";
import { RuleCategorySection } from "@/components/RuleCategorySection";
import { RuleSheet } from "@/components/RuleSheet";
import { ManageCategoriesDialog } from "@/components/ManageCategoriesDialog";

import type { Rule, RuleCategory } from "@/lib/types";
import { createRule, updateRule, deleteRule, updateRuleCategory, deleteRuleCategory } from "@/lib/api";
import type { RuleFormData } from "@/components/RuleSheet";
import { useRules } from "@/lib/useRules";
import { useRuleCategories } from "@/lib/useRuleCategories";
import { useMistakes } from "@/lib/useMistakes";

const JOURNAL_TABS = [
  { label: "Trades", href: "/journal" },
  { label: "Calendar", href: "/journal/calendar" },
  { label: "Mistakes", href: "/journal/mistakes" },
  { label: "Rules", href: "/journal/rules" },
];

const UNCATEGORIZED = "Uncategorized";

interface RuleGroup {
  name: string;
  rules: Rule[];
  totalBreaks: number;
}

function groupRules(rules: Rule[]): RuleGroup[] {
  const map = new Map<string, Rule[]>();
  for (const rule of rules) {
    const key = rule.category?.name ?? UNCATEGORIZED;
    const existing = map.get(key) ?? [];
    map.set(key, [...existing, rule]);
  }
  const groups: RuleGroup[] = [];
  map.forEach((groupRules, name) => {
    groups.push({ name, rules: groupRules, totalBreaks: groupRules.reduce((s, r) => s + r.break_count, 0) });
  });
  groups.sort((a, b) => {
    if (a.name === UNCATEGORIZED) return 1;
    if (b.name === UNCATEGORIZED) return -1;
    return b.totalBreaks - a.totalBreaks;
  });
  return groups;
}

export default function RulesPage() {
  const pathname = usePathname();
  const { rules, loading, error, refetch } = useRules();
  const { categories, refetch: refetchCategories } = useRuleCategories();
  const { mistakes } = useMistakes();

  const [sheetOpen, setSheetOpen] = useState(false);
  const [editingRule, setEditingRule] = useState<Rule | null>(null);
  const [manageCatsOpen, setManageCatsOpen] = useState(false);
  const [mutationError, setMutationError] = useState<string | null>(null);
  const [extraCategories, setExtraCategories] = useState<RuleCategory[]>([]);

  const allCategories = useMemo(
    () => [...categories, ...extraCategories.filter((ec) => !categories.some((c) => c.id === ec.id))],
    [categories, extraCategories]
  );

  const groups = useMemo(() => groupRules(rules), [rules]);

  function openNew() {
    setEditingRule(null);
    setSheetOpen(true);
  }

  function openEdit(rule: Rule) {
    setEditingRule(rule);
    setSheetOpen(true);
  }

  const handleSave = useCallback(async (data: RuleFormData) => {
    try {
      if (editingRule) {
        await updateRule(editingRule.id, {
          title: data.title,
          body: data.body || null,
          category_id: data.categoryId,
          linked_mistake_ids: data.linkedMistakeIds,
        });
      } else {
        await createRule({
          title: data.title,
          body: data.body || null,
          category_id: data.categoryId,
          linked_mistake_ids: data.linkedMistakeIds,
        });
      }
      setMutationError(null);
      refetch();
    } catch (e) {
      setMutationError(e instanceof Error ? e.message : "Failed to save rule");
      throw e;
    }
  }, [editingRule, refetch]);

  const handleDelete = useCallback(async (id: string) => {
    try {
      await deleteRule(id);
      setMutationError(null);
      refetch();
    } catch (e) {
      setMutationError(e instanceof Error ? e.message : "Failed to delete rule");
      throw e;
    }
  }, [refetch]);

  async function handleRenameCategory(id: string, name: string) {
    await updateRuleCategory(id, name);
    refetchCategories();
    refetch();
  }

  async function handleDeleteCategory(id: string) {
    await deleteRuleCategory(id);
    refetchCategories();
    refetch();
  }

  const displayError = mutationError ?? error;

  return (
    <div className="p-6">
      <Link
        href="/"
        className="text-xs text-[#777777] hover:text-[#e0e0e0] transition-colors inline-flex items-center gap-1 mb-3"
      >
        ← Dashboard
      </Link>

      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-[#e0e0e0]">Journal</h1>
      </div>

      <div className="flex gap-2 mb-6">
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

      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-sm font-medium text-[#e0e0e0]">Rules</h2>
          <button
            type="button"
            onClick={() => setManageCatsOpen(true)}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors"
          >
            [Manage Categories]
          </button>
        </div>
        <Button size="sm" onClick={openNew}>+ New Rule</Button>
      </div>

      {displayError && (
        <p className="text-xs text-[#ef5350] mb-4">{displayError}</p>
      )}

      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 rounded bg-[#1e1e1e] animate-pulse" />
          ))}
        </div>
      ) : rules.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-sm text-muted-foreground mb-1">No rules written yet.</p>
          <p className="text-xs text-muted-foreground mb-4">
            Rules are principles you trade by. Write the first one above.
          </p>
          <p className="text-xs text-[#555555] mb-6">
            Common categories: Entry · Pre-Market · Risk · Psychology
          </p>
          <Button size="sm" onClick={openNew}>+ Write your first rule</Button>
        </div>
      ) : (
        <div>
          {groups.map((group) => (
            <RuleCategorySection
              key={group.name}
              categoryName={group.name}
              rules={group.rules}
              onEdit={openEdit}
              onDelete={(id) => void handleDelete(id)}
            />
          ))}
        </div>
      )}

      <RuleSheet
        rule={editingRule}
        categories={allCategories}
        mistakes={mistakes}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
        onSave={handleSave}
        onDelete={editingRule ? handleDelete : undefined}
        onCategoryCreated={(cat) => setExtraCategories((prev) => [...prev, cat])}
      />

      <ManageCategoriesDialog
        open={manageCatsOpen}
        onOpenChange={setManageCatsOpen}
        categories={allCategories}
        rules={rules}
        onRename={handleRenameCategory}
        onDelete={handleDeleteCategory}
      />
    </div>
  );
}
