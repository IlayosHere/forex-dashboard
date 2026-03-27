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
        isSelected ? "bg-[#1e1e1e]" : "bg-[#161616] hover:bg-[#1a1a1a]"
      }`}
      style={{ borderLeftColor: isBuy ? "#26a69a" : "#ef5350" }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span
            className="text-base leading-none"
            style={{ color: isBuy ? "#26a69a" : "#ef5350" }}
          >
            {isBuy ? "▲" : "▼"}
          </span>
          <span className="font-bold text-[#e0e0e0]">{signal.symbol}</span>
          <span
            className="text-xs font-medium"
            style={{ color: isBuy ? "#26a69a" : "#ef5350" }}
          >
            {signal.direction}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-[#777777]">{formatTime(signal.candle_time)}</span>
          {isSelected && (
            <span className="text-[#26a69a] text-xs leading-none">●</span>
          )}
        </div>
      </div>
    </div>
  );
}
