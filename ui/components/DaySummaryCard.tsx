"use client";

import Link from "next/link";

import type { TradingFeeling } from "@/lib/types";

import { usePremarketPlan } from "@/lib/usePremarketPlan";
import { useSession } from "@/lib/useSession";
import { FEELING_OPTIONS } from "@/lib/feelings";

interface DaySummaryCardProps {
  date: string;
  /** Optional override for the "view full day" label — defaults to "View full day". */
  linkLabel?: string;
  /** Where the day page's back-link should return to. Defaults to /journal. */
  backHref?: string;
  /** Label for that back-link. Defaults to "Back to Journal". */
  backLabel?: string;
}

const BIAS_COLORS: Record<string, string> = {
  bullish: "#26a69a",
  bearish: "#ef5350",
  neutral: "#777777",
};

function moodColor(feeling: TradingFeeling | null): string {
  if (!feeling) return "#3a3a3a";
  const opt = FEELING_OPTIONS.find((f) => f.value === feeling);
  return opt?.sentiment === "positive" ? "#26a69a" : "#ef5350";
}

function MoodDot({ label, feeling }: { label: string; feeling: TradingFeeling | null }) {
  return (
    <span
      title={`${label}: ${feeling ?? "not logged"}`}
      className="w-2 h-2 rounded-full inline-block"
      style={{ backgroundColor: moodColor(feeling) }}
    />
  );
}

export function DaySummaryCard({ date, linkLabel = "View full day", backHref, backLabel }: DaySummaryCardProps) {
  const { plan, loading: planLoading } = usePremarketPlan(date);
  const { session, loading: sessionLoading } = useSession(date);

  const loading = planLoading || sessionLoading;
  const scenarioCount = plan?.scenarios.length ?? 0;
  const biasColor = plan?.daily_bias ? BIAS_COLORS[plan.daily_bias] : "#555555";

  const params = new URLSearchParams();
  if (backHref) params.set("back", backHref);
  if (backLabel) params.set("backLabel", backLabel);
  const query = params.toString();
  const href = `/journal/day/${date}${query ? `?${query}` : ""}`;

  return (
    <div className="flex items-center justify-between px-3 py-2 mb-3 rounded border border-border bg-card text-xs">
      <div className="flex items-center gap-3">
        {loading ? (
          <span className="text-text-dim">—</span>
        ) : (
          <>
            <span style={{ color: biasColor }} className="font-medium capitalize">
              {plan?.daily_bias ?? "No bias"}
            </span>
            <span className="text-text-muted">
              {scenarioCount} scenario{scenarioCount === 1 ? "" : "s"}
            </span>
            <span className="flex items-center gap-1">
              <MoodDot label="Pre" feeling={session?.feeling_pre ?? null} />
              <MoodDot label="During" feeling={session?.feeling_during ?? null} />
              <MoodDot label="Post" feeling={session?.feeling_post ?? null} />
            </span>
          </>
        )}
      </div>
      <Link
        href={href}
        className="text-text-muted hover:text-text-primary transition-colors"
      >
        {linkLabel} →
      </Link>
    </div>
  );
}
