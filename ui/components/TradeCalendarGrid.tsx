"use client";

import { useMemo } from "react";

import { CalendarDayCell } from "@/components/CalendarDayCell";
import { WeekSummaryCell } from "@/components/WeekSummaryCell";

import type { DailySummaryPoint, PremarketDaySummary } from "@/lib/types";

export interface TradeCalendarGridProps {
  year: number;
  month: number;
  dailyData: DailySummaryPoint[];
  premarketData?: PremarketDaySummary[];
  selectedDate: string | null;
  showMoney: boolean;
  onDaySelect: (date: string | null) => void;
  renderDayPanel?: (date: string) => React.ReactNode;
}

const WEEKDAY_HEADERS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const GRID_COLS = "grid-cols-[3.5rem_repeat(7,1fr)]";

function computeWeekSummary(
  week: Array<string | null>,
  dataMap: Map<string, DailySummaryPoint>,
): { pnl: number; pnlR: number; trades: number; wins: number; losses: number } {
  let pnl = 0; let pnlR = 0; let trades = 0; let wins = 0; let losses = 0;
  for (const date of week) {
    if (!date) continue;
    const d = dataMap.get(date);
    if (!d) continue;
    pnl += d.pnl_usd;
    pnlR += d.pnl_r;
    trades += d.trades;
    wins += d.wins;
    losses += d.losses;
  }
  return { pnl, pnlR, trades, wins, losses };
}

function toUTCDateKey(d: Date): string {
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, "0")}-${String(d.getUTCDate()).padStart(2, "0")}`;
}

function buildWeeks(year: number, month: number): Array<Array<string | null>> {
  // month is 1-indexed
  const firstDay = new Date(Date.UTC(year, month - 1, 1));
  const lastDay = new Date(Date.UTC(year, month, 0));

  // Monday = 0, Sunday = 6
  const startDow = (firstDay.getUTCDay() + 6) % 7;
  const daysInMonth = lastDay.getUTCDate();

  const weeks: Array<Array<string | null>> = [];
  let week: Array<string | null> = [];

  // Leading padding
  for (let i = 0; i < startDow; i++) {
    week.push(null);
  }

  for (let day = 1; day <= daysInMonth; day++) {
    const d = new Date(Date.UTC(year, month - 1, day));
    week.push(toUTCDateKey(d));
    if (week.length === 7) {
      weeks.push(week);
      week = [];
    }
  }

  // Trailing padding
  if (week.length > 0) {
    while (week.length < 7) week.push(null);
    weeks.push(week);
  }

  return weeks;
}

export function TradeCalendarGrid({
  year,
  month,
  dailyData,
  premarketData = [],
  selectedDate,
  showMoney,
  onDaySelect,
  renderDayPanel,
}: TradeCalendarGridProps) {
  const dataMap = useMemo(() => {
    const m = new Map<string, DailySummaryPoint>();
    for (const d of dailyData) m.set(d.date, d);
    return m;
  }, [dailyData]);

  const premarketMap = useMemo(() => {
    const m = new Map<string, PremarketDaySummary>();
    for (const d of premarketData) m.set(d.date, d);
    return m;
  }, [premarketData]);

  const weeks = useMemo(() => buildWeeks(year, month), [year, month]);

  const todayKey = useMemo(() => toUTCDateKey(new Date()), []);

  const selectedWeekIndex = useMemo(() => {
    if (!selectedDate) return -1;
    return weeks.findIndex((week) => week.includes(selectedDate));
  }, [selectedDate, weeks]);

  function handleDayClick(date: string) {
    onDaySelect(date === selectedDate ? null : date);
  }

  return (
    <div>
      {/* Weekday header row */}
      <div className={`grid ${GRID_COLS} gap-1 mb-1`}>
        {/* Summary column header — matches cell width */}
        <div className="text-[10px] uppercase tracking-widest text-[#444] text-left pl-2 py-2">
          Wk
        </div>
        {WEEKDAY_HEADERS.map((label) => (
          <div
            key={label}
            className="text-[10px] uppercase tracking-widest text-[#444] text-center py-2"
          >
            {label}
          </div>
        ))}
      </div>

      {/* Week rows */}
      {weeks.map((week, weekIdx) => {
        const summary = computeWeekSummary(week, dataMap);
        return (
        <div key={weekIdx}>
          <div className={`grid ${GRID_COLS} gap-1 mb-1`}>
            <WeekSummaryCell
              pnl={summary.pnl}
              pnlR={summary.pnlR}
              tradeCount={summary.trades}
              wins={summary.wins}
              losses={summary.losses}
              showMoney={showMoney}
              weekDate={week.find((d) => d !== null) ?? undefined}
            />
            {week.map((date, colIdx) =>
              date === null ? (
                <div
                  key={colIdx}
                  className="bg-[#0a0a0a] rounded-md h-16 sm:h-24 opacity-20"
                  aria-hidden="true"
                />
              ) : (
                <CalendarDayCell
                  key={date}
                  date={date}
                  pnl={dataMap.get(date)?.pnl_usd ?? 0}
                  pnlR={dataMap.get(date)?.pnl_r ?? 0}
                  tradeCount={dataMap.get(date)?.trades ?? 0}
                  wins={dataMap.get(date)?.wins ?? 0}
                  losses={dataMap.get(date)?.losses ?? 0}
                  mistakes={dataMap.get(date)?.mistakes ?? 0}
                  dailyBias={premarketMap.has(date) ? (premarketMap.get(date)?.daily_bias ?? "neutral") : null}
                  isToday={date === todayKey}
                  isSelected={date === selectedDate}
                  isCurrentMonth={date.startsWith(`${year}-${String(month).padStart(2, "0")}`)}
                  showMoney={showMoney}
                  onClick={() => handleDayClick(date)}
                />
              )
            )}
          </div>

          {/* Inline day panel rendered after the matching week */}
          {selectedWeekIndex === weekIdx &&
            selectedDate &&
            renderDayPanel &&
            renderDayPanel(selectedDate)}
        </div>
        );
      })}
    </div>
  );
}
