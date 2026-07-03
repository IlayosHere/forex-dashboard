"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { LifeCalendarGrid } from "@/components/LifeCalendarGrid";
import { LifeDaySheet } from "@/components/LifeDaySheet";

import { fetchLifeSummary } from "@/lib/api";
import { useLifeEntries } from "@/lib/useLifeEntries";
import type { LifeEntry, LifeSummaryPoint } from "@/lib/types";

function LifeCalendarContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const now = new Date();
  const yearParam = searchParams.get("year");
  const monthParam = searchParams.get("month");
  const year = yearParam ? parseInt(yearParam, 10) : now.getFullYear();
  const month = monthParam ? parseInt(monthParam, 10) : now.getMonth();

  const [summary, setSummary] = useState<LifeSummaryPoint[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [dayEntries, setDayEntries] = useState<LifeEntry[]>([]);

  const from = `${year}-${String(month + 1).padStart(2, "0")}-01T00:00:00Z`;
  const lastDay = new Date(year, month + 1, 0).getDate();
  const to = `${year}-${String(month + 1).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}T23:59:59Z`;

  const { entries } = useLifeEntries({ from, to, limit: 200 });

  useEffect(() => {
    fetchLifeSummary(from, to).then(setSummary).catch(() => {});
  }, [from, to]);

  const monthLabel = new Date(year, month).toLocaleDateString([], { month: "long", year: "numeric" });

  function navigate(delta: number) {
    const d = new Date(year, month + delta);
    const params = new URLSearchParams({ year: String(d.getFullYear()), month: String(d.getMonth()) });
    router.replace(`/life/calendar?${params.toString()}`);
  }

  function handleDayClick(date: string) {
    const matched = entries.filter((e) => e.entry_at.slice(0, 10) === date);
    setDayEntries(matched);
    setSelectedDate(date);
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => navigate(-1)}>‹</Button>
          <span className="text-sm font-medium text-text-primary w-36 text-center">{monthLabel}</span>
          <Button size="sm" variant="outline" onClick={() => navigate(1)}>›</Button>
        </div>
        <Link href="/life" className="text-sm text-text-muted hover:text-text-primary transition-colors">
          ← Timeline
        </Link>
      </div>

      <LifeCalendarGrid
        year={year}
        month={month}
        summary={summary}
        onDayClick={handleDayClick}
      />

      <LifeDaySheet
        date={selectedDate}
        entries={dayEntries}
        onClose={() => setSelectedDate(null)}
      />
    </div>
  );
}

export default function LifeCalendarPage() {
  return (
    <Suspense fallback={<p className="text-text-muted text-sm p-6">Loading…</p>}>
      <LifeCalendarContent />
    </Suspense>
  );
}
