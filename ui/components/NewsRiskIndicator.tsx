"use client";

import { useState, useEffect } from "react";

import { fetchCalendar } from "@/lib/api";

import type { CalendarEvent } from "@/lib/types";

interface NewsRiskIndicatorProps {
  symbol: string;
}

// Store the epoch ms of each event so msUntil is recomputed at render time
interface UpcomingEvent {
  name: string;
  currency: string;
  atMs: number;
}

const FOUR_HOURS_MS = 4 * 60 * 60 * 1000;
const REFRESH_INTERVAL_MS = 60 * 1000;

function deriveCurrencies(symbol: string): [string, string] {
  return [symbol.slice(0, 3).toUpperCase(), symbol.slice(3, 6).toUpperCase()];
}

function formatMinutesUntil(ms: number): string {
  const totalMinutes = Math.floor(ms / 60000);
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  if (h === 0) return `${m}m`;
  return `${h}h ${m}m`;
}

function filterUpcoming(events: CalendarEvent[], symbol: string): UpcomingEvent[] {
  const now = Date.now();
  const [ccy1, ccy2] = deriveCurrencies(symbol);
  return events
    .filter((ev) => {
      if (ev.impact !== "High" && !ev.promoted) return false;
      if (ev.currency !== ccy1 && ev.currency !== ccy2) return false;
      const msUntil = new Date(ev.datetime_utc).getTime() - now;
      return msUntil > 0 && msUntil <= FOUR_HOURS_MS;
    })
    .map((ev) => ({
      name: ev.name,
      currency: ev.currency,
      atMs: new Date(ev.datetime_utc).getTime(),
    }))
    .sort((a, b) => a.atMs - b.atMs);
}

export function NewsRiskIndicator({ symbol }: NewsRiskIndicatorProps) {
  const [upcoming, setUpcoming] = useState<UpcomingEvent[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const events = await fetchCalendar("current");
        if (!cancelled) setUpcoming(filterUpcoming(events, symbol));
      } catch {
        // silent — this is supplementary UI
      }
    }

    void load();
    const intervalId = setInterval(() => { void load(); }, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [symbol]);

  // Filter out events that have now passed (recomputed each render)
  const now = Date.now();
  const visible = upcoming.filter((ev) => ev.atMs - now > 0);

  if (visible.length === 0) return null;

  return (
    <div className="bg-elevated rounded px-3 py-2">
      <p className="text-[9px] uppercase tracking-widest text-text-dim mb-1">News Risk</p>
      <p className="text-xs text-accent-gold leading-snug">
        {visible.map((ev, i) => (
          <span key={`${ev.currency}-${ev.name}`}>
            {i > 0 && <span className="text-text-dim mx-1.5">·</span>}
            <span className="font-medium">{ev.currency}</span>
            {" "}
            {ev.name}
            {" "}
            <span className="text-accent-gold/70">in {formatMinutesUntil(ev.atMs - now)}</span>
          </span>
        ))}
      </p>
    </div>
  );
}
