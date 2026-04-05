"use client";

import { useState, useEffect, useCallback, useMemo } from "react";

import { BASE_URL } from "@/lib/api";
import type { CalendarContext, CalendarEvent } from "@/lib/types";
const POLL_INTERVAL_MS = 5 * 60 * 1000;

export interface UseCalendarResult {
  events: CalendarEvent[];
  byDay: Record<string, CalendarEvent[]>;
  loading: boolean;
  error: string | null;
}

interface UseCalendarOptions {
  week: "current" | "next";
  context: CalendarContext;
}

function isMnqRelevant(event: CalendarEvent): boolean {
  if (event.currency === "USD") return true;
  if (event.currency === "CNY" && event.name.includes("China PMI")) return true;
  if (event.currency === "JPY" && event.name.includes("BOJ")) return true;
  return false;
}

function groupByDay(events: CalendarEvent[]): Record<string, CalendarEvent[]> {
  const result: Record<string, CalendarEvent[]> = {};
  for (const ev of events) {
    const day = ev.datetime_utc.slice(0, 10);
    if (!result[day]) result[day] = [];
    result[day].push(ev);
  }
  return result;
}

export function useCalendar({ week, context }: UseCalendarOptions): UseCalendarResult {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await fetch(`${BASE_URL}/api/calendar?week=${week}`, {
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`Calendar fetch failed: ${res.status}`);
      const data = (await res.json()) as CalendarEvent[];
      const filtered = context === "mnq" ? data.filter(isMnqRelevant) : data;
      setEvents(filtered);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load calendar");
    } finally {
      setLoading(false);
    }
  }, [week, context]);

  useEffect(() => {
    setLoading(true);
    void fetchData();
    const id = setInterval(() => void fetchData(), POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchData]);

  const byDay = useMemo(() => groupByDay(events), [events]);

  return { events, byDay, loading, error };
}
