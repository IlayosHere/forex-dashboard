import { STATUS_ORDER, statusLabel } from "@/lib/researchFormat";
import type { IdeaStatus } from "@/lib/researchTypes";

export type StatusFilter = IdeaStatus | "all";
export type StageFilter = "all" | "1" | "2" | "3";

interface IdeaFiltersProps {
  counts: Record<IdeaStatus, number>;
  total: number;
  status: StatusFilter;
  stage: StageFilter;
  query: string;
  onStatus: (value: StatusFilter) => void;
  onStage: (value: StageFilter) => void;
  onQuery: (value: string) => void;
}

function Chip({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={`rounded-full border px-3 py-1 text-xs transition-colors ${
        active ? "border-border-light bg-elevated text-text-primary" : "border-border text-text-muted hover:text-text-primary"
      }`}
    >
      {children}
    </button>
  );
}

export function IdeaFilters(props: IdeaFiltersProps) {
  const { counts, total, status, stage, query } = props;
  return (
    <div className="mb-5 space-y-3">
      <div className="flex flex-wrap gap-2">
        <Chip active={status === "all"} onClick={() => props.onStatus("all")}>
          All {total}
        </Chip>
        {STATUS_ORDER.map((s) => (
          <Chip key={s} active={status === s} onClick={() => props.onStatus(s)}>
            {statusLabel(s)} {counts[s]}
          </Chip>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={query}
          onChange={(e) => props.onQuery(e.target.value)}
          placeholder="Search ideas"
          aria-label="Search ideas"
          className="w-56 rounded border border-border bg-surface-input px-3 py-1.5 text-sm text-text-primary placeholder:text-text-dim"
        />
        <select
          value={stage}
          onChange={(e) => props.onStage(e.target.value as StageFilter)}
          aria-label="Filter by stage"
          className="rounded border border-border bg-surface-input px-2 py-1.5 text-sm text-text-primary"
        >
          <option value="all">All stages</option>
          <option value="1">Stage 1</option>
          <option value="2">Stage 2</option>
          <option value="3">Stage 3</option>
        </select>
      </div>
    </div>
  );
}
