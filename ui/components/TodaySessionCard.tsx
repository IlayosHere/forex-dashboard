"use client";

import type { TradingSession } from "@/lib/types";

interface TodaySessionCardProps {
  session: TradingSession | null;
  loading: boolean;
  onLog: () => void;
}

function planLabel(session: TradingSession | null): { text: string; color: string } {
  if (session === null) return { text: "Not logged", color: "#555555" };
  if (session.had_pre_session_plan === null) return { text: "Not logged", color: "#555555" };
  return session.had_pre_session_plan
    ? { text: "Setup in mind", color: "#26a69a" }
    : { text: "No setup today", color: "#777777" };
}

export function TodaySessionCard({ session, loading, onLog }: TodaySessionCardProps) {
  const plan = planLabel(session);

  return (
    <div className="flex items-center justify-between px-3 py-2 mb-3 rounded border border-border bg-card text-xs">
      <div className="flex items-center gap-3">
        <span className="text-text-muted uppercase tracking-wider text-[10px]">Today's session</span>
        {loading ? (
          <span className="text-text-dim">—</span>
        ) : (
          <span style={{ color: plan.color }} className="font-medium">{plan.text}</span>
        )}
      </div>
      <button
        type="button"
        onClick={onLog}
        className="text-text-muted hover:text-text-primary transition-colors cursor-pointer"
      >
        Log →
      </button>
    </div>
  );
}
