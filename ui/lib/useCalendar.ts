"use client";

import { useState, useEffect, useCallback, useRef } from "react";

import { fetchCalendar } from "@/lib/api";
import type { CalendarEvent } from "@/lib/types";

// Calendar data is weekly — 5-minute poll is intentional, not the 30s project default
const POLL_INTERVAL_MS = 5 * 60 * 1000;

export interface UseCalendarResult {
  events: CalendarEvent[];
  loading: boolean;
  error: string | null;
}

interface UseCalendarOptions {
  week: "current" | "next";
}

function isMnqRelevant(event: CalendarEvent): boolean {
  if (event.currency === "USD") return true;
  if (event.currency === "CNY" && event.name.includes("China PMI")) return true;
  if (event.currency === "JPY" && event.name.includes("BOJ")) return true;
  return false;
}

export function useCalendar({ week }: UseCalendarOptions): UseCalendarResult {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cancelRef = useRef(0);

  const loadData = useCallback(async () => {
    const id = ++cancelRef.current;
    try {
      const data = await fetchCalendar(week);
      if (cancelRef.current !== id) return;
      setEvents(data.filter(isMnqRelevant));
      setError(null);
    } catch (err) {
      if (cancelRef.current !== id) return;
      setError(err instanceof Error ? err.message : "Failed to load calendar");
    } finally {
      if (cancelRef.current === id) setLoading(false);
    }
  }, [week]);

  useEffect(() => {
    setLoading(true);
    void loadData();
    const id = setInterval(() => void loadData(), POLL_INTERVAL_MS);
    return () => {
      cancelRef.current++;
      clearInterval(id);
    };
  }, [loadData]);

  return { events, loading, error };
}
