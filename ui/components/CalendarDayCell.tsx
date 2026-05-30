"use client";

import type { DailySummaryPoint } from "@/lib/types";

export interface CalendarDayCellProps {
  date: string;
  pnl: number;
  pnlR: number;
  tradeCount: number;
  wins: number;
  losses: number;
  mistakes?: number;
  isToday: boolean;
  isSelected: boolean;
  isCurrentMonth: boolean;
  showMoney: boolean;
  onClick: () => void;
}

function formatPnl(pnl: number): string {
  if (pnl >= 0) return `+$${pnl.toFixed(2)}`;
  return `-$${Math.abs(pnl).toFixed(2)}`;
}

function formatR(r: number): string {
  if (r >= 0) return `+${r.toFixed(2)}R`;
  return `${r.toFixed(2)}R`;
}

function getDayNumber(date: string): number {
  return parseInt(date.split("-")[2], 10);
}

function accentColor(pnl: number, tradeCount: number): string {
  if (tradeCount === 0) return "transparent";
  if (pnl > 0) return "#26a69a";
  if (pnl < 0) return "#ef5350";
  return "transparent";
}

function pnlTextColor(pnl: number): string {
  if (pnl > 0) return "#26a69a";
  if (pnl < 0) return "#ef5350";
  return "#777777";
}

export function CalendarDayCell({
  date,
  pnl,
  pnlR,
  tradeCount,
  wins,
  losses,
  mistakes = 0,
  isToday,
  isSelected,
  isCurrentMonth,
  showMoney,
  onClick,
}: CalendarDayCellProps) {
  const hasTrades = tradeCount > 0;
  const dayNumber = getDayNumber(date);

  const borderClass = isSelected
    ? "border-[#26a69a]"
    : hasTrades
    ? "border-[#2a2a2a]"
    : "border-[#1e1e1e]";

  const bgClass = hasTrades ? "bg-[#111111]" : "bg-[#0d0d0d]";
  const ringClass = isToday ? "ring-1 ring-[#3b82f6]/40" : "";
  const opacityClass = !hasTrades ? "opacity-60" : "";
  const cursorClass = hasTrades ? "cursor-pointer" : "cursor-default";
  const hoverClass = hasTrades ? "hover:border-[#333] hover:bg-[#161616]" : "";

  return (
    <div
      role={hasTrades ? "button" : undefined}
      tabIndex={hasTrades ? 0 : undefined}
      onClick={hasTrades ? onClick : undefined}
      onKeyDown={
        hasTrades
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") onClick();
            }
          : undefined
      }
      aria-label={
        hasTrades
          ? `${date}: ${tradeCount} trades, ${showMoney ? `P&L ${formatPnl(pnl)}` : formatR(pnlR)}`
          : date
      }
      aria-pressed={hasTrades ? isSelected : undefined}
      className={[
        "relative rounded-md border transition-colors duration-100 p-2 flex flex-col justify-between",
        "h-16 sm:h-24",
        borderClass,
        bgClass,
        ringClass,
        opacityClass,
        cursorClass,
        hoverClass,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {/* Left accent bar */}
      <div
        aria-hidden="true"
        className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-md"
        style={{ backgroundColor: accentColor(pnl, tradeCount) }}
      />

      {/* Mistake dot — shown when any trades had rule violations */}
      {mistakes > 0 && (
        <div
          aria-label={`${mistakes} mistake trade${mistakes > 1 ? "s" : ""}`}
          className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-amber-500"
        />
      )}

      {/* Date number */}
      <div
        className={`text-xs font-medium pl-1 ${
          isCurrentMonth ? "text-[#e0e0e0]" : "text-[#777]"
        }`}
      >
        {dayNumber}
      </div>

      {/* P&L / R */}
      {hasTrades && (
        <div
          className="text-sm font-semibold tabular-nums pl-1 leading-tight"
          style={{ color: pnlTextColor(showMoney ? pnl : pnlR) }}
        >
          {showMoney ? formatPnl(pnl) : formatR(pnlR)}
        </div>
      )}

      {/* Trade count / W / L */}
      {hasTrades && (
        <div className="text-[10px] text-[#777] pl-1">
          {tradeCount} tr · {wins}W {losses}L
        </div>
      )}
    </div>
  );
}

// Re-export type for convenience
export type { DailySummaryPoint };
