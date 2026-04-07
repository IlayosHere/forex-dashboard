"use client";

import type { CalendarContext, CalendarImpact } from "@/lib/types";

interface CalendarFiltersProps {
  context: CalendarContext;
  onContextChange: (ctx: CalendarContext) => void;
  week: "current" | "next";
  onWeekChange: (w: "current" | "next") => void;
  impactFilter: CalendarImpact[];
  onImpactChange: (impacts: CalendarImpact[]) => void;
  currencyFilter: string;
  onCurrencyChange: (cur: string) => void;
}

const IMPACT_OPTIONS: CalendarImpact[] = ["High", "Medium", "Low"];
const CURRENCIES = ["All", "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "NZD", "CHF", "CNY"];

const pillBase = "px-3 py-1 text-xs rounded-full border transition-colors cursor-pointer";
const pillActive = "border-primary bg-primary/10 text-primary";
const pillInactive = "border-border text-muted-foreground hover:border-border-light hover:text-foreground";

const ctxBase = "px-3 py-1 text-xs font-medium border transition-colors cursor-pointer";
const ctxActive = "border-primary bg-primary/10 text-primary";
const ctxInactive = "border-border text-muted-foreground hover:border-border-light hover:text-foreground";

function isDefault(
  context: CalendarContext,
  week: "current" | "next",
  impactFilter: CalendarImpact[],
  currencyFilter: string,
): boolean {
  const defaultCurrency = context === "mnq" ? "USD" : "All";
  return (
    week === "current" &&
    impactFilter.length === 1 &&
    impactFilter[0] === "High" &&
    currencyFilter === defaultCurrency
  );
}

function toggleImpact(current: CalendarImpact[], impact: CalendarImpact): CalendarImpact[] {
  return current.includes(impact)
    ? current.filter((i) => i !== impact)
    : [...current, impact];
}

export function CalendarFilters({
  context,
  onContextChange,
  week,
  onWeekChange,
  impactFilter,
  onImpactChange,
  currencyFilter,
  onCurrencyChange,
}: CalendarFiltersProps) {
  const showReset = !isDefault(context, week, impactFilter, currencyFilter);
  const defaultCurrency = context === "mnq" ? "USD" : "All";

  function handleReset() {
    onWeekChange("current");
    onImpactChange(["High"]);
    onCurrencyChange(defaultCurrency);
  }

  return (
    <div className="flex flex-wrap items-center gap-3 px-4 py-3 border-b border-border">
      {/* Context toggle */}
      <div className="flex rounded overflow-hidden border border-border">
        {(["forex", "mnq"] as CalendarContext[]).map((ctx) => (
          <button
            key={ctx}
            type="button"
            onClick={() => onContextChange(ctx)}
            className={`${ctxBase} ${context === ctx ? ctxActive : ctxInactive} ${ctx === "forex" ? "border-r border-border" : ""}`}
          >
            {ctx === "forex" ? "Forex" : "MNQ"}
          </button>
        ))}
      </div>

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

      {/* Currency filter */}
      <select
        className="bg-elevated border border-border text-sm text-foreground rounded px-2 py-1 outline-none focus:border-primary cursor-pointer"
        value={currencyFilter}
        onChange={(e) => onCurrencyChange(e.target.value)}
      >
        {CURRENCIES.map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>

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
