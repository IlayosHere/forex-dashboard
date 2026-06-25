"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import type { PlanScenario } from "@/lib/types";

import { fetchPlanScenario } from "@/lib/api";

interface LinkedScenarioCardProps {
  scenarioId: string;
}

function joinParts(parts: (string | null)[]): string | null {
  const filtered = parts.filter((p): p is string => Boolean(p));
  return filtered.length > 0 ? filtered.join(" · ") : null;
}

export function LinkedScenarioCard({ scenarioId }: LinkedScenarioCardProps) {
  const [scenario, setScenario] = useState<PlanScenario | null>(null);

  useEffect(() => {
    fetchPlanScenario(scenarioId).then(setScenario).catch(() => setScenario(null));
  }, [scenarioId]);

  if (!scenario) return null;

  const area = joinParts([scenario.reaction_setup_type, scenario.reaction_setup_detail]);
  const target = joinParts([scenario.target_level_type, scenario.target_level_detail]);

  return (
    <div className="border border-border rounded-lg p-3 bg-card mb-4 space-y-1.5">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
          From Pre-Market Scenario
        </p>
        <Link href={`/journal/day/${scenario.date}`} className="text-[11px] text-text-muted hover:text-bull transition-colors">
          View day &rarr;
        </Link>
      </div>
      {area && (
        <div className="flex gap-2 text-xs">
          <span className="text-text-muted w-20 shrink-0">Area</span>
          <span className="text-text-primary">{area}</span>
        </div>
      )}
      {target && (
        <div className="flex gap-2 text-xs">
          <span className="text-text-muted w-20 shrink-0">Target / DOL</span>
          <span className="text-text-primary">{target}</span>
        </div>
      )}
      {scenario.notes && (
        <div className="flex gap-2 text-xs">
          <span className="text-text-muted w-20 shrink-0">Notes</span>
          <span className="text-text-primary">{scenario.notes}</span>
        </div>
      )}
    </div>
  );
}
