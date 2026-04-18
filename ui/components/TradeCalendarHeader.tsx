"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

export interface TradeCalendarHeaderProps {
  year: number;
  month: number;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
}

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

export function TradeCalendarHeader({
  year,
  month,
  onPrev,
  onNext,
  onToday,
}: TradeCalendarHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-4">
      <button
        type="button"
        onClick={onPrev}
        aria-label="Previous month"
        className="p-1.5 rounded hover:bg-[#1e1e1e] text-[#777] hover:text-[#e0e0e0] transition-colors"
      >
        <ChevronLeft size={16} />
      </button>

      <span className="text-sm font-medium text-[#e0e0e0]">
        {MONTH_NAMES[month - 1]} {year}
      </span>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToday}
          aria-label="Go to today"
          className="text-xs px-2.5 py-1 rounded border border-[#2a2a2a] text-[#777] hover:text-[#e0e0e0] hover:border-[#444] transition-colors"
        >
          Today
        </button>
        <button
          type="button"
          onClick={onNext}
          aria-label="Next month"
          className="p-1.5 rounded hover:bg-[#1e1e1e] text-[#777] hover:text-[#e0e0e0] transition-colors"
        >
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
