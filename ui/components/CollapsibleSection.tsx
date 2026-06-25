"use client";

import { ChevronRight } from "lucide-react";

interface CollapsibleSectionProps {
  title: string;
  summary: string;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  /** When false, renders as a static always-open section with no toggle affordance. */
  collapsible?: boolean;
}

export function CollapsibleSection({
  title,
  summary,
  expanded,
  onToggle,
  children,
  collapsible = true,
}: CollapsibleSectionProps) {
  const header = (
    <span className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left">
      <span className={`text-sm font-semibold shrink-0 ${expanded ? "text-text-primary" : "text-text-muted"}`}>
        {title}
      </span>
      <span className="flex items-center gap-3 min-w-0">
        {!expanded && <span className="text-xs text-text-muted truncate">{summary}</span>}
        {collapsible && (
          <ChevronRight
            size={14}
            className={`text-text-muted shrink-0 transition-transform ${expanded ? "rotate-90" : ""}`}
          />
        )}
      </span>
    </span>
  );

  return (
    <div
      className={`border rounded-lg mb-4 transition-colors ${
        expanded ? "border-border-light bg-surface-raised" : "border-border bg-card"
      }`}
    >
      {collapsible ? (
        <button type="button" onClick={onToggle} className="w-full cursor-pointer">
          {header}
        </button>
      ) : (
        header
      )}
      {expanded && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}
