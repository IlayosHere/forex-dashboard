import type { MarketClosure } from "@/lib/types";

interface CalendarClosedPanelProps {
  closure: MarketClosure;
}

export function CalendarClosedPanel({ closure }: CalendarClosedPanelProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
      <span className="text-sm font-semibold text-bear uppercase tracking-widest">
        CME Globex Closed
      </span>
      <span className="text-sm text-foreground">{closure.label}</span>
      <span className="text-xs text-text-dim">{closure.note}</span>
    </div>
  );
}
