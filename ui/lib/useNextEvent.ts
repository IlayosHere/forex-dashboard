"use client";

import type { CalendarEvent } from "@/lib/types";

export interface UseNextEventResult {
  event: CalendarEvent | null;
  secondsUntil: number;
}

function findNextHighImpact(events: CalendarEvent[], now: Date): CalendarEvent | null {
  const upcoming = events
    .filter((ev) => (ev.impact === "High" || ev.promoted) && new Date(ev.datetime_utc) > now)
    .sort((a, b) => new Date(a.datetime_utc).getTime() - new Date(b.datetime_utc).getTime());
  return upcoming[0] ?? null;
}

function calcSecondsUntil(event: CalendarEvent | null, now: Date): number {
  if (!event) return 0;
  return Math.max(0, Math.floor((new Date(event.datetime_utc).getTime() - now.getTime()) / 1000));
}

export function useNextEvent(events: CalendarEvent[], now: Date): UseNextEventResult {
  const event = findNextHighImpact(events, now);
  const secondsUntil = calcSecondsUntil(event, now);

  return { event, secondsUntil };
}
