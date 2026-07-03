"use client";

import type { CalendarImpact } from "@/lib/types";

interface CalendarFiltersProps {
  week: "current" | "next";
  onWeekChange: (w: "current" | "next") => void;
  impactFilter: CalendarImpact[];
  onImpactChange: (impacts: CalendarImpact[]) => void;
}

const IMPACT_OPTIONS: CalendarImpact[] = ["High", "Medium", "Low"];

const pillBase = "px-3 py-1 text-xs rounded-full border transition-colors cursor-pointer";
const pillActive = "border-primary bg-primary/10 text-primary";
const pillInactive = "border-border text-muted-foreground hover:border-border-light hover:text-foreground";

function isDefault(week: "current" | "next", impactFilter: CalendarImpact[]): boolean {
  return week === "current" && impactFilter.length === 1 && impactFilter[0] === "High";
}

function toggleImpact(current: CalendarImpact[], impact: CalendarImpact): CalendarImpact[] {
  return current.includes(impact)
    ? current.filter((i) => i !== impact)
    : [...current, impact];
}

export function CalendarFilters({
  week,
  onWeekChange,
  impactFilter,
  onImpactChange,
}: CalendarFiltersProps) {
  const showReset = !isDefault(week, impactFilter);

  function handleReset() {
    onWeekChange("current");
    onImpactChange(["High"]);
  }

  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-border">
      {/* Week nav */}
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={() => onWeekChange("current")}
          className="px-1.5 py-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
          aria-label="Previous week"
        >
          ‹
        </button>
        <span className="text-xs text-foreground px-2 py-1 border border-border rounded min-w-[80px] text-center">
          {week === "current" ? "This Week" : "Next Week"}
        </span>
        <button
          type="button"
          onClick={() => onWeekChange("next")}
          className="px-1.5 py-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer transition-colors"
          aria-label="Next week"
        >
          ›
        </button>
      </div>

      {/* Impact toggles */}
      <div className="flex gap-1">
        {IMPACT_OPTIONS.map((impact) => (
          <button
            key={impact}
            type="button"
            onClick={() => onImpactChange(toggleImpact(impactFilter, impact))}
            className={`${pillBase} ${impactFilter.includes(impact) ? pillActive : pillInactive}`}
          >
            {impact === "Medium" ? "Med" : impact}
          </button>
        ))}
      </div>

      {/* Reset link */}
      {showReset && (
        <button
          type="button"
          onClick={handleReset}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
        >
          Reset filters
        </button>
      )}
    </div>
  );
}
