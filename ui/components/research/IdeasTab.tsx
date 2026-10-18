"use client";

import { useMemo, useState } from "react";

import { STATUS_ORDER, countByStatus, matchesSearch, statusLabel, statusMeaning } from "@/lib/researchFormat";
import type { IdeaStatus, ResearchIdea } from "@/lib/researchTypes";

import { IdeaCard } from "./IdeaCard";
import { IdeaFilters } from "./IdeaFilters";
import type { StageFilter, StatusFilter } from "./IdeaFilters";

interface IdeasTabProps {
  ideas: ResearchIdea[];
  onOpenReport: (path: string) => void;
}

function inStage(idea: ResearchIdea, stage: StageFilter): boolean {
  return stage === "all" || idea.stage.split(",").includes(stage);
}

export function IdeasTab({ ideas, onOpenReport }: IdeasTabProps) {
  const [status, setStatus] = useState<StatusFilter>("all");
  const [stage, setStage] = useState<StageFilter>("all");
  const [query, setQuery] = useState("");
  const [showKilled, setShowKilled] = useState(false);

  const counts = useMemo(() => countByStatus(ideas), [ideas]);
  const visible = useMemo(
    () => ideas.filter((i) => (status === "all" || i.status === status) && inStage(i, stage) && matchesSearch(i, query)),
    [ideas, status, stage, query],
  );
  const killedOpen = showKilled || status === "killed" || query.trim() !== "";

  return (
    <div>
      <IdeaFilters
        counts={counts} total={ideas.length} status={status} stage={stage} query={query}
        onStatus={setStatus} onStage={setStage} onQuery={setQuery}
      />
      {STATUS_ORDER.map((group: IdeaStatus) => {
        const items = visible.filter((i) => i.status === group);
        if (items.length === 0) return null;
        const hidden = group === "killed" && !killedOpen;
        return (
          <section key={group} className="mb-6">
            <div className="mb-2 flex items-baseline gap-3">
              <h2 className="text-sm font-semibold text-text-primary">
                {statusLabel(group)} <span className="font-normal text-text-dim">{items.length}</span>
              </h2>
              <p className="text-xs text-text-muted">{statusMeaning(group)}</p>
            </div>
            {hidden ? (
              <button type="button" onClick={() => setShowKilled(true)} className="text-xs text-breakeven hover:underline">
                Show the {items.length} killed ideas
              </button>
            ) : (
              <div className="space-y-2">
                {items.map((idea) => (
                  <IdeaCard key={idea.id} idea={idea} onOpenReport={onOpenReport} />
                ))}
              </div>
            )}
          </section>
        );
      })}
      {visible.length === 0 && <p className="text-sm text-text-muted">No ideas match these filters.</p>}
    </div>
  );
}
