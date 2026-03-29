"use client";

import type { Signal } from "@/lib/types";

interface SignalCardProps {
  signal: Signal;
  isSelected: boolean;
  onClick: () => void;
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    const hh = d.getUTCHours().toString().padStart(2, "0");
    const mm = d.getUTCMinutes().toString().padStart(2, "0");
    return `${hh}:${mm} UTC`;
  } catch {
    return "—";
  }
}

export function SignalCard({ signal, isSelected, onClick }: SignalCardProps) {
  const isBuy = signal.direction === "BUY";

  return (
    <div
      onClick={onClick}
      data-interactive
      className={`cursor-pointer w-full px-3 py-2.5 border-l-2 ${
        isBuy ? "border-l-bull" : "border-l-bear"
      } ${
        isSelected ? "bg-elevated" : "bg-card hover:bg-surface-raised"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className={`text-base leading-none ${isBuy ? "text-bull" : "text-bear"}`}
          >
            {isBuy ? "▲" : "▼"}
          </span>
          <span className="font-bold text-foreground">{signal.symbol}</span>
          <span
            className={`text-xs font-medium ${isBuy ? "text-bull" : "text-bear"}`}
          >
            {signal.direction}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">{formatTime(signal.candle_time)}</span>
          {isSelected && (
            <span className="text-bull text-xs leading-none">●</span>
          )}
        </div>
      </div>
    </div>
  );
}
