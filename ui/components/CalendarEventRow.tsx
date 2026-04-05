import type { BeatMiss, CalendarContext, CalendarEvent } from "@/lib/types";

interface CalendarEventRowProps {
  event: CalendarEvent;
  context: CalendarContext;
  isPast: boolean;
}

const LEFT_BORDER: Record<string, string> = {
  High: "border-l-2 border-l-[#e6a800]",
  Medium: "border-l-2 border-l-[#777777]",
  Low: "border-l-2 border-l-[#333333]",
};

function formatActual(actual: string | null, beatMiss: BeatMiss): { text: string; className: string } {
  if (actual === null || beatMiss === "pending") {
    return { text: "—", className: "text-[#444444]" };
  }
  if (beatMiss === "beat") return { text: `▲ ${actual}`, className: "text-[#26a69a]" };
  if (beatMiss === "miss") return { text: `▼ ${actual}`, className: "text-[#ef5350]" };
  return { text: actual, className: "text-[#777777]" };
}

function formatTime(event: CalendarEvent, context: CalendarContext): string {
  const iso = context === "mnq" ? event.datetime_et : event.datetime_utc;
  return iso.slice(11, 16);
}

export function CalendarEventRow({ event, context, isPast }: CalendarEventRowProps) {
  const borderClass = LEFT_BORDER[event.impact] ?? LEFT_BORDER["Low"];
  const rowBase = `grid grid-cols-[4px_52px_52px_1fr_72px_72px_80px] gap-x-3 items-center px-3 py-1.5 text-xs ${borderClass}`;
  const rowStateClass = isPast
    ? "opacity-50"
    : "hover:bg-[#1a1a1a] transition-colors cursor-default";

  const { text: actualText, className: actualClass } = formatActual(event.actual, event.beat_miss);

  return (
    <div className={`${rowBase} ${rowStateClass}`} role="row">
      <span />
      <span className="font-mono text-[#777777] tabular-nums">
        {formatTime(event, context)}
      </span>
      <span className="font-semibold text-[#e0e0e0] uppercase tracking-wide text-[10px]">
        {event.currency}
      </span>
      <span className="text-[#c0c0c0] truncate">
        {event.name}
        {event.promoted && (
          <span className="ml-1 text-[9px] text-[#e6a800] uppercase tracking-widest">promo</span>
        )}
      </span>
      <span className="text-[#555555] text-right tabular-nums">
        {event.previous ?? "—"}
      </span>
      <span className="text-[#777777] text-right tabular-nums">
        {event.forecast ?? "—"}
      </span>
      <span className={`text-right tabular-nums font-medium ${actualClass}`}>
        {actualText}
      </span>
    </div>
  );
}
