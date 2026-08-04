"use client";

import Link from "next/link";

import { useCalendar } from "@/lib/useCalendar";
import { useMarketHolidays } from "@/lib/useMarketHolidays";
import { useNextEvent } from "@/lib/useNextEvent";
import type { CalendarEvent } from "@/lib/types";

export interface TodayNewsStripProps {
  /** ISO date (YYYY-MM-DD), ET — same "today" the rest of the Journal page uses. */
  date: string;
}

const IMPACT_BADGE_CLASS: Record<string, string> = {
  High: "bg-warning/15 text-warning border border-warning/40",
  Medium: "bg-accent-gold/15 text-accent-gold border border-accent-gold/30",
};

function formatEventTime(event: CalendarEvent): string {
  return `${event.datetime_et.slice(11, 16)} ET`;
}

function isToday(event: CalendarEvent, date: string): boolean {
  return event.datetime_et.slice(0, 10) === date;
}

export function TodayNewsStrip({ date }: TodayNewsStripProps) {
  // Same feed/cache /calendar uses — no second poller.
  const { events } = useCalendar({ week: "current" });
  const { closures } = useMarketHolidays({ week: "current" });
  const todaysEvents = events.filter((ev) => isToday(ev, date));
  // Scoped to today only, unlike /calendar's week-wide next-event strip.
  const { event } = useNextEvent(todaysEvents, new Date());
  const closure = closures.find((c) => c.date === date) ?? null;

  if (closure?.closure_type === "full_close") {
    return (
      <div className="flex items-center gap-3 px-3 py-2 mb-3 rounded border border-bear/30 bg-card text-xs">
        <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide bg-bear/15 text-bear border border-bear/30">
          Closed
        </span>
        <span className="text-text-primary font-medium flex-1 truncate">{closure.label}</span>
      </div>
    );
  }

  if (!event) {
    return (
      <div className="flex items-center px-3 py-2 mb-3 rounded border border-border bg-card text-xs text-text-dim">
        No high-impact news today
      </div>
    );
  }

  const badgeClass = IMPACT_BADGE_CLASS[event.impact] ?? IMPACT_BADGE_CLASS["Medium"];

  return (
    <Link
      href="/calendar"
      className="flex items-center gap-3 px-3 py-2 mb-3 rounded border border-border bg-card text-xs hover:border-border-light transition-colors"
    >
      {closure?.closure_type === "early_close" && (
        <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide text-text-dim border border-border-light shrink-0">
          Early close {closure.early_close_et} ET
        </span>
      )}
      <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wide shrink-0 ${badgeClass}`}>
        {event.impact}
      </span>
      <span className="text-text-muted font-semibold uppercase tracking-wide shrink-0">
        {event.currency}
      </span>
      <span className="text-text-primary font-medium flex-1 truncate">{event.name}</span>
      <span className="text-text-dim shrink-0">{formatEventTime(event)}</span>
    </Link>
  );
}
