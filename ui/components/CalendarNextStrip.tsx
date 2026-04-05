import type { CalendarContext, CalendarEvent } from "@/lib/types";

interface CalendarNextStripProps {
  event: CalendarEvent | null;
  secondsUntil: number;
  context: CalendarContext;
}

const LIVE_THRESHOLD_SECONDS = 300;

function formatCountdown(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

function formatEventTime(event: CalendarEvent, context: CalendarContext): string {
  const iso = context === "mnq" ? event.datetime_et : event.datetime_utc;
  const suffix = context === "mnq" ? " ET" : " UTC";
  return `${iso.slice(11, 16)}${suffix}`;
}

const IMPACT_BADGE_CLASS: Record<string, string> = {
  High: "bg-[#e6a800]/15 text-[#e6a800] border border-[#e6a800]/30",
  Medium: "bg-[#777777]/15 text-[#777777] border border-[#777777]/30",
  Low: "bg-[#333333]/15 text-[#555555] border border-[#333333]/30",
};

export function CalendarNextStrip({ event, secondsUntil, context }: CalendarNextStripProps) {
  if (!event) return null;

  const isLive = secondsUntil <= LIVE_THRESHOLD_SECONDS;
  const countdownClass = isLive
    ? "font-mono text-sm tabular-nums text-[#ef5350]"
    : "font-mono text-sm tabular-nums text-[#e6a800]";

  const badgeClass = IMPACT_BADGE_CLASS[event.impact] ?? IMPACT_BADGE_CLASS["Low"];

  return (
    <div className="w-full h-[52px] flex items-center gap-4 px-6 bg-[#161616] border-b border-[#2a2a2a]">
      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide ${badgeClass}`}>
        {event.impact}
      </span>
      <span className="text-xs font-semibold text-[#777777] uppercase tracking-wide">
        {event.currency}
      </span>
      <span className="text-sm text-[#e0e0e0] font-medium flex-1 truncate">
        {event.name}
      </span>
      <span className="text-xs text-[#555555]">
        {formatEventTime(event, context)}
      </span>
      <span className={countdownClass}>
        {isLive ? "RELEASING NOW" : formatCountdown(secondsUntil)}
      </span>
    </div>
  );
}
