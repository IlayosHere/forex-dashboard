"use client";

import { useSignalScore } from "@/lib/useSignalScore";
import { GradeBadge } from "@/components/GradeBadge";
import { GateStatusBadge } from "@/components/GateStatusBadge";

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

function ScoreBadge({ score, maxPossible }: { score: number; maxPossible: number }) {
  if (maxPossible === 0) return null;
  const color =
    score > 0 ? "text-bull" : score < 0 ? "text-bear" : "text-muted-foreground";
  const sign = score > 0 ? "+" : "";
  return (
    <span className={`text-[10px] font-medium tabular-nums ${color}`}>
      {sign}{score} / {maxPossible}
    </span>
  );
}

export function SignalCard({ signal, isSelected, onClick }: SignalCardProps) {
  const isBuy = signal.direction === "BUY";
  const { data: scoreData, loading: scoreLoading, fetch: fetchScore } = useSignalScore(
    signal.id,
    signal.strategy,
  );

  function handleMouseEnter() {
    if (!scoreData && !scoreLoading) {
      fetchScore();
    }
  }

  return (
    <div
      onClick={onClick}
      onMouseEnter={handleMouseEnter}
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
          <GradeBadge grade={signal.grade} size="xs" />
        </div>
        <div className="flex items-center gap-1.5">
          {signal.gate_status === "blocked" && (
            <GateStatusBadge status={signal.gate_status} />
          )}
          {scoreData && scoreData.max_possible > 0 && (
            <ScoreBadge score={scoreData.score} maxPossible={scoreData.max_possible} />
          )}
          <span className="text-xs text-muted-foreground">{formatTime(signal.candle_time)}</span>
          {isSelected && (
            <span className="text-bull text-xs leading-none">●</span>
          )}
        </div>
      </div>
    </div>
  );
}
