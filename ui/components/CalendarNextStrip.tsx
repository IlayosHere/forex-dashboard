import type { CalendarEvent, MarketClosure } from "@/lib/types";

interface CalendarNextStripProps {
  event: CalendarEvent | null;
  secondsUntil: number;
  closure?: MarketClosure | null;
}

const LIVE_THRESHOLD_SECONDS = 300;

function formatCountdown(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}

function formatEventTime(event: CalendarEvent): string {
  return `${event.datetime_et.slice(11, 16)} ET`;
}

const IMPACT_BADGE_CLASS: Record<string, string> = {
  High: "bg-accent-gold/15 text-accent-gold border border-accent-gold/30",
  Medium: "bg-muted-foreground/15 text-muted-foreground border border-muted-foreground/30",
  Low: "bg-border-light/15 text-text-dim border border-border-light/30",
};

export function CalendarNextStrip({ event, secondsUntil, closure }: CalendarNextStripProps) {
  if (closure?.closure_type === "full_close") {
    return (
      <div className="w-full h-[52px] flex items-center gap-3 px-6 bg-card border-b border-bear/30">
        <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide bg-bear/15 text-bear border border-bear/30">
          Closed
        </span>
        <span className="text-sm text-foreground font-medium flex-1 truncate">
          {closure.label}
        </span>
        <span className="text-xs text-text-dim">{closure.note}</span>
      </div>
    );
  }

  if (!event) return null;

  const isLive = secondsUntil <= LIVE_THRESHOLD_SECONDS;
  const countdownClass = isLive
    ? "font-mono text-sm tabular-nums text-accent-gold animate-pulse"
    : "font-mono text-sm tabular-nums text-accent-gold";

  const badgeClass = IMPACT_BADGE_CLASS[event.impact] ?? IMPACT_BADGE_CLASS["Low"];

  return (
    <div className="w-full h-[52px] flex items-center gap-4 px-6 bg-card border-b border-border">
      {closure?.closure_type === "early_close" && (
        <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide text-text-dim border border-border-light">
          Early close {closure.early_close_et} ET
        </span>
      )}
      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide ${badgeClass}`}>
        {event.impact}
      </span>
      <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
        {event.currency}
      </span>
      <span className="text-sm text-foreground font-medium flex-1 truncate">
        {event.name}
      </span>
      <span className="text-xs text-text-dim">
        {formatEventTime(event)}
      </span>
      <span className={countdownClass}>
        {isLive ? "RELEASING NOW" : formatCountdown(secondsUntil)}
      </span>
    </div>
  );
}
