"use client";

import { useRegime } from "@/lib/useRegime";

import type { RegimeStatus } from "@/lib/types";

interface RegimeBannerProps {
  strategy: string;
  symbol?: string;
}

const STATUS_CONFIG: Record<
  Exclude<RegimeStatus, "insufficient_data">,
  { border: string; bg: string; dot: string; text: string }
> = {
  healthy: {
    border: "border-l-bull",
    bg: "bg-bull/10",
    dot: "bg-bull",
    text: "text-bull",
  },
  warning: {
    border: "border-l-amber-400",
    bg: "bg-amber-400/10",
    dot: "bg-amber-400",
    text: "text-amber-400",
  },
  degraded: {
    border: "border-l-bear",
    bg: "bg-bear/10",
    dot: "bg-bear",
    text: "text-bear",
  },
};

function formatPct(rate: number): string {
  return `${Math.round(rate * 100)}%`;
}

function bannerMessage(
  status: Exclude<RegimeStatus, "insufficient_data">,
  recentRate: number,
  priorRate: number,
): string {
  const recent = formatPct(recentRate);
  const prior = formatPct(priorRate);
  if (status === "healthy") {
    return `Strategy performing as expected (recent 30 trades: ${recent} win rate)`;
  }
  if (status === "warning") {
    return `Win rate shift detected — recent 30 trades: ${recent} vs prior 30: ${prior}. Monitor closely.`;
  }
  return `Significant win rate decline — recent 30 trades: ${recent} vs prior 30: ${prior}. Review conditions.`;
}

export function RegimeBanner({ strategy, symbol }: RegimeBannerProps) {
  const { data } = useRegime(strategy, symbol);

  if (!data || data.status === "insufficient_data") return null;

  const status = data.status as Exclude<RegimeStatus, "insufficient_data">;
  const cfg = STATUS_CONFIG[status];
  const message = bannerMessage(status, data.recent.win_rate, data.prior.win_rate);

  return (
    <div
      className={`mb-4 flex items-center gap-3 rounded border-l-4 px-4 py-2.5 ${cfg.border} ${cfg.bg}`}
    >
      <span className={`h-2 w-2 shrink-0 rounded-full ${cfg.dot}`} />
      <p className={`text-xs font-medium ${cfg.text}`}>{message}</p>
    </div>
  );
}
