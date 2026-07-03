"use client";

import { use } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { DayWorkspace } from "@/components/DayWorkspace";

import { addDays, formatDate, nowNYDatetime } from "@/lib/dates";

interface DayPageProps {
  params: Promise<{ date: string }>;
}

export default function DayPage({ params }: DayPageProps) {
  const { date } = use(params);
  const searchParams = useSearchParams();
  const backHref = searchParams.get("back") ?? "/journal";
  const backLabel = searchParams.get("backLabel") ?? "Back to Journal";

  const query = searchParams.toString();
  const dayHref = (d: string) => `/journal/day/${d}${query ? `?${query}` : ""}`;
  const today = nowNYDatetime().slice(0, 10);

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Link
            href={dayHref(addDays(date, -1))}
            aria-label="Previous day"
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            <ChevronLeft size={16} />
          </Link>
          <h1 className="text-lg font-semibold text-text-primary">{formatDate(date)}</h1>
          <Link
            href={dayHref(addDays(date, 1))}
            aria-label="Next day"
            className="text-text-muted hover:text-text-primary transition-colors"
          >
            <ChevronRight size={16} />
          </Link>
          {date !== today && (
            <Link href={dayHref(today)} className="text-xs text-text-muted hover:text-bull transition-colors ml-1">
              Today
            </Link>
          )}
        </div>
        <Link href={backHref} className="text-xs text-text-muted hover:text-text-primary">
          {backLabel}
        </Link>
      </div>
      <DayWorkspace date={date} />
    </div>
  );
}
