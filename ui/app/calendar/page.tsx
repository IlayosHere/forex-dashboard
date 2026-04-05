"use client";

import { useState, useEffect, useMemo } from "react";

import { CalendarDaySection } from "@/components/CalendarDaySection";
import { CalendarFilters } from "@/components/CalendarFilters";
import { CalendarNextStrip } from "@/components/CalendarNextStrip";
import { CalendarTimeGroup } from "@/components/CalendarTimeGroup";
import { useCalendar } from "@/lib/useCalendar";
import { useNextEvent } from "@/lib/useNextEvent";
import { getTodayKeyUTC } from "@/lib/utils";

import type { CalendarContext, CalendarEvent, CalendarImpact, SessionBucket } from "@/lib/types";

const SESSION_LABELS: Record<SessionBucket, string> = {
  pre_market: "Pre-Market",
  cash_session: "Cash Session",
  none: "Other",
};

const tabClass = (active: boolean) =>
  `px-4 py-2 text-sm font-medium transition-colors cursor-pointer -mb-px ${
    active
      ? "text-[#26a69a] border-b-2 border-[#26a69a]"
      : "text-[#777777] hover:text-[#e0e0e0] border-b-2 border-transparent"
  }`;

function applyFilters(
  events: CalendarEvent[],
  impactFilter: CalendarImpact[],
  currencyFilter: string,
): CalendarEvent[] {
  return events.filter((ev) => {
    const impactMatch = impactFilter.includes(ev.impact);
    const currencyMatch = currencyFilter === "All" || ev.currency === currencyFilter;
    return impactMatch && currencyMatch;
  });
}

function groupByTimeSlot(events: CalendarEvent[], context: CalendarContext): Record<string, CalendarEvent[]> {
  const result: Record<string, CalendarEvent[]> = {};
  for (const ev of events) {
    const iso = context === "mnq" ? ev.datetime_et : ev.datetime_utc;
    const label = iso.slice(11, 16);
    if (!result[label]) result[label] = [];
    result[label].push(ev);
  }
  return result;
}

function groupBySession(events: CalendarEvent[]): Record<SessionBucket, CalendarEvent[]> {
  const buckets: Record<SessionBucket, CalendarEvent[]> = {
    pre_market: [],
    cash_session: [],
    none: [],
  };
  for (const ev of events) {
    buckets[ev.session_bucket].push(ev);
  }
  return buckets;
}

export default function CalendarPage() {
  const [context, setContext] = useState<CalendarContext>("forex");
  const [week, setWeek] = useState<"current" | "next">("current");
  const [impactFilter, setImpactFilter] = useState<CalendarImpact[]>(["High"]);
  const [currencyFilter, setCurrencyFilter] = useState("All");
  const [activeTab, setActiveTab] = useState<"today" | "week">("today");

  const { events, loading } = useCalendar({ week, context });
  const { event: nextEvent, secondsUntil } = useNextEvent(events);

  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const todayKey = useMemo(() => getTodayKeyUTC(), []);

  const filteredEvents = useMemo(
    () => applyFilters(events, impactFilter, currencyFilter),
    [events, impactFilter, currencyFilter],
  );

  const filteredByDay = useMemo(() => {
    const result: Record<string, CalendarEvent[]> = {};
    for (const ev of filteredEvents) {
      const day = ev.datetime_utc.slice(0, 10);
      if (!result[day]) result[day] = [];
      result[day].push(ev);
    }
    return result;
  }, [filteredEvents]);

  const todayEvents = filteredByDay[todayKey] ?? [];
  const todayGroups = useMemo(() => {
    if (context === "mnq") {
      return (["pre_market", "cash_session", "none"] as SessionBucket[])
        .map((bucket) => ({ label: SESSION_LABELS[bucket], events: groupBySession(todayEvents)[bucket] }))
        .filter((g) => g.events.length > 0);
    }
    return Object.entries(groupByTimeSlot(todayEvents, context))
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([timeLabel, slotEvents]) => ({ label: `${timeLabel} UTC`, events: slotEvents }));
  }, [todayEvents, context]);
  const sortedDays = useMemo(() => Object.keys(filteredByDay).sort(), [filteredByDay]);

  function handleContextChange(ctx: CalendarContext) {
    setContext(ctx);
    setCurrencyFilter(ctx === "mnq" ? "USD" : "All");
  }

  if (loading) {
    return (
      <div className="p-6 space-y-2">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="bg-[#1e1e1e] animate-pulse rounded h-8" />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <CalendarNextStrip event={nextEvent} secondsUntil={secondsUntil} context={context} />

      <CalendarFilters
        context={context}
        onContextChange={handleContextChange}
        week={week}
        onWeekChange={setWeek}
        impactFilter={impactFilter}
        onImpactChange={setImpactFilter}
        currencyFilter={currencyFilter}
        onCurrencyChange={setCurrencyFilter}
      />

      <div className="flex gap-0 border-b border-[#2a2a2a] px-4">
        <button type="button" className={tabClass(activeTab === "today")} onClick={() => setActiveTab("today")}>
          Today
        </button>
        <button type="button" className={tabClass(activeTab === "week")} onClick={() => setActiveTab("week")}>
          This Week
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {activeTab === "today" && (
          <>
            {todayEvents.length === 0 && (
              <div className="flex items-center justify-center py-16 text-sm text-[#555555]">
                No events match the current filters.
              </div>
            )}
            {todayGroups.map(({ label, events: groupEvents }) => (
              <CalendarTimeGroup
                key={label}
                timeLabel={label}
                events={groupEvents}
                context={context}
                currentTime={now}
              />
            ))}
          </>
        )}

        {activeTab === "week" && (
          <>
            {sortedDays.length === 0 && (
              <div className="flex items-center justify-center py-16 text-sm text-[#555555]">
                No events match the current filters.
              </div>
            )}
            {sortedDays.map((day) => (
              <CalendarDaySection
                key={day}
                date={day}
                events={filteredByDay[day]}
                context={context}
                defaultOpen={day === todayKey}
              />
            ))}
          </>
        )}
      </div>
    </div>
  );
}
