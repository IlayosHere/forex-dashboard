"use client";

import { MOOD_CONFIG } from "@/lib/moodConfig";
import type { LifeSummaryPoint } from "@/lib/types";

interface LifeCalendarGridProps {
  year: number;
  month: number;
  summary: LifeSummaryPoint[];
  onDayClick: (date: string) => void;
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstWeekday(year: number, month: number): number {
  return new Date(year, month, 1).getDay();
}

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

const WEEKDAYS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

export function LifeCalendarGrid({ year, month, summary, onDayClick }: LifeCalendarGridProps) {
  const byDate = new Map(summary.map((s) => [s.date, s]));
  const daysInMonth = getDaysInMonth(year, month);
  const firstWeekday = getFirstWeekday(year, month);

  const cells: (number | null)[] = [
    ...Array(firstWeekday).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];

  return (
    <div className="space-y-1">
      <div className="grid grid-cols-7 gap-1 mb-1">
        {WEEKDAYS.map((d) => (
          <div key={d} className="text-center text-[10px] text-text-dim font-medium py-1">{d}</div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((day, i) => {
          if (day === null) return <div key={`e-${i}`} />;
          const dateStr = `${year}-${pad2(month + 1)}-${pad2(day)}`;
          const point = byDate.get(dateStr);
          const moodCfg = point?.dominant_mood ? MOOD_CONFIG[point.dominant_mood] : null;
          const accentColor = moodCfg?.color;

          return (
            <button
              key={dateStr}
              type="button"
              onClick={() => onDayClick(dateStr)}
              className={`flex flex-col items-center justify-center aspect-square rounded text-xs transition-colors cursor-pointer ${
                point ? "bg-surface-raised hover:bg-elevated" : "bg-surface hover:bg-surface-raised"
              } border border-border`}
              style={accentColor ? { backgroundColor: `${accentColor}22` } : undefined}
            >
              <span className={point ? "text-text-primary font-medium" : "text-text-muted"}>
                {day}
              </span>
              {point && (
                <span className="text-[10px] text-text-muted">{point.count}</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
