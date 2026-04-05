"use client";

import { useState } from "react";

import { CalendarEventRow } from "@/components/CalendarEventRow";
import { getTodayKeyUTC } from "@/lib/utils";

import type { CalendarContext, CalendarEvent, CalendarImpact } from "@/lib/types";

interface CalendarDaySectionProps {
  date: string;
  events: CalendarEvent[];
  context: CalendarContext;
  defaultOpen: boolean;
  currentTime: Date;
}

const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

function parseDateLabel(dateStr: string): { dayName: string; formatted: string; isToday: boolean } {
  const [year, month, day] = dateStr.split("-").map(Number);
  const d = new Date(Date.UTC(year, month - 1, day));
  return {
    dayName: DAY_NAMES[d.getUTCDay()],
    formatted: `${String(month).padStart(2, "0")}/${String(day).padStart(2, "0")}`,
    isToday: dateStr === getTodayKeyUTC(),
  };
}

function buildSummary(events: CalendarEvent[]): string {
  const highCount = events.filter((e) => e.impact === "High" || e.promoted).length;
  const impactCounts: Record<CalendarImpact, number> = { High: 0, Medium: 0, Low: 0 };
  for (const ev of events) impactCounts[ev.impact]++;
  if (highCount > 0) return `${highCount} high-impact event${highCount !== 1 ? "s" : ""}`;
  if (impactCounts.Medium > 0) return `${impactCounts.Medium} medium-impact event${impactCounts.Medium !== 1 ? "s" : ""}`;
  return `${events.length} event${events.length !== 1 ? "s" : ""}`;
}

export function CalendarDaySection({ date, events, context, defaultOpen, currentTime }: CalendarDaySectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  const { dayName, formatted, isToday } = parseDateLabel(date);

  const headerColorClass = isToday
    ? "text-accent-gold border-accent-gold/20"
    : "text-text-dim border-border";

  return (
    <div className="border-b border-border">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`w-full flex items-center justify-between px-4 py-2 border-b ${headerColorClass} hover:bg-surface-raised transition-colors cursor-pointer`}
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-widest">
            {dayName}
          </span>
          <span className="text-[10px] text-text-dim">{formatted}</span>
          {isToday && (
            <span className="text-[9px] uppercase tracking-widest text-accent-gold bg-accent-gold/10 px-1.5 py-0.5 rounded-full">
              Today
            </span>
          )}
        </span>
        <span className="flex items-center gap-3">
          {!open && (
            <span className="text-[10px] text-text-dim">{buildSummary(events)}</span>
          )}
          <span className="text-text-dim text-xs">{open ? "▲" : "▼"}</span>
        </span>
      </button>

      {open && (
        <div role="table" aria-label={`Events for ${dayName} ${formatted}`}>
          {events.map((event) => (
            <CalendarEventRow
              key={event.id}
              event={event}
              context={context}
              isPast={new Date(event.datetime_utc) < currentTime}
            />
          ))}
        </div>
      )}
    </div>
  );
}
