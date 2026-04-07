"use client";

import { useState, useEffect, useCallback } from "react";

import { fetchCalendar } from "@/lib/api";
import type { CalendarContext, CalendarEvent } from "@/lib/types";

// Calendar data is weekly — 5-minute poll is intentional, not the 30s project default
const POLL_INTERVAL_MS = 5 * 60 * 1000;

export interface UseCalendarResult {
  events: CalendarEvent[];
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

export function useCalendar({ week, context }: UseCalendarOptions): UseCalendarResult {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await fetchCalendar(week);
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
    void loadData();
    const id = setInterval(() => void loadData(), POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [loadData]);

  return { events, loading, error };
}
