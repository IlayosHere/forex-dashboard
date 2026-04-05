"use client";

import { useState, useEffect } from "react";

import { BASE_URL } from "@/lib/api";
import type { CalendarEvent } from "@/lib/types";

interface NewsRiskIndicatorProps {
  symbol: string;
}
const FOUR_HOURS_MS = 4 * 60 * 60 * 1000;

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

export function NewsRiskIndicator({ symbol }: NewsRiskIndicatorProps) {
  const [upcoming, setUpcoming] = useState<{ name: string; currency: string; msUntil: number }[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const res = await fetch(`${BASE_URL}/api/calendar?week=current`, { cache: "no-store" });
        if (!res.ok) return;
        const events = (await res.json()) as CalendarEvent[];
        const now = Date.now();
        const [ccy1, ccy2] = deriveCurrencies(symbol);
        const relevant = events
          .filter((ev) => {
            if (ev.impact !== "High" && !ev.promoted) return false;
            if (ev.currency !== ccy1 && ev.currency !== ccy2) return false;
            const msUntil = new Date(ev.datetime_utc).getTime() - now;
            return msUntil > 0 && msUntil <= FOUR_HOURS_MS;
          })
          .map((ev) => ({
            name: ev.name,
            currency: ev.currency,
            msUntil: new Date(ev.datetime_utc).getTime() - now,
          }))
          .sort((a, b) => a.msUntil - b.msUntil);
        if (!cancelled) setUpcoming(relevant);
      } catch {
        // silent — this is supplementary UI
      }
    }

    void load();
    return () => { cancelled = true; };
  }, [symbol]);

  if (upcoming.length === 0) return null;

  return (
    <div className="bg-[#1e1e1e] rounded px-3 py-2">
      <p className="text-[9px] uppercase tracking-widest text-[#444444] mb-1">News Risk</p>
      <p className="text-xs text-[#e6a800] leading-snug">
        {upcoming.map((ev, i) => (
          <span key={i}>
            {i > 0 && <span className="text-[#444444] mx-1.5">·</span>}
            <span className="font-medium">{ev.currency}</span>
            {" "}
            {ev.name}
            {" "}
            <span className="text-[#c08000]">in {formatMinutesUntil(ev.msUntil)}</span>
          </span>
        ))}
      </p>
    </div>
  );
}
