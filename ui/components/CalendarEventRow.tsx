import type { BeatMiss, CalendarContext, CalendarEvent } from "@/lib/types";

interface CalendarEventRowProps {
  event: CalendarEvent;
  context: CalendarContext;
  isPast: boolean;
}

const LEFT_BORDER: Record<string, string> = {
  High: "border-l-2 border-l-accent-gold",
  Medium: "border-l-2 border-l-muted-foreground",
  Low: "border-l-2 border-l-border-light",
};

function formatActual(actual: string | null, beatMiss: BeatMiss): { text: string; className: string } {
  if (actual === null || beatMiss === "pending") {
    return { text: "—", className: "text-text-dim" };
  }
  if (beatMiss === "beat") return { text: `▲ ${actual}`, className: "text-primary" };
  if (beatMiss === "miss") return { text: `▼ ${actual}`, className: "text-bear" };
  return { text: actual, className: "text-muted-foreground" };
}

function formatTime(event: CalendarEvent, context: CalendarContext): string {
  const iso = context === "mnq" ? event.datetime_et : event.datetime_utc;
  return iso.slice(11, 16);
}

export function CalendarEventRow({ event, context, isPast }: CalendarEventRowProps) {
  const borderClass = LEFT_BORDER[event.impact] ?? LEFT_BORDER["Low"];
  const rowBase = `overflow-x-auto grid grid-cols-[4px_52px_52px_1fr_72px_72px_80px] gap-x-3 items-center px-3 py-1.5 text-xs ${borderClass}`;
  const rowStateClass = isPast
    ? "opacity-50"
    : "hover:bg-surface-raised transition-colors cursor-default";

  const { text: actualText, className: actualClass } = formatActual(event.actual, event.beat_miss);

  return (
    <div className={`${rowBase} ${rowStateClass}`} role="row">
      <span />
      <span className="font-mono text-muted-foreground tabular-nums">
        {formatTime(event, context)}
      </span>
      <span className="font-semibold text-foreground uppercase tracking-wide text-[10px]">
        {event.currency}
      </span>
      <span className="text-muted-foreground truncate">
        {event.name}
        {event.promoted && (
          <span className="ml-1 text-[9px] text-accent-gold uppercase tracking-widest">promo</span>
        )}
      </span>
      <span className="text-text-dim text-right tabular-nums">
        {event.previous ?? "—"}
      </span>
      <span className="text-muted-foreground text-right tabular-nums">
        {event.forecast ?? "—"}
      </span>
      <span className={`text-right tabular-nums font-medium ${actualClass}`}>
        {actualText}
      </span>
    </div>
  );
}
