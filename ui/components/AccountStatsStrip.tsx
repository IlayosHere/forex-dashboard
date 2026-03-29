"use client";

import type { TradeStats } from "@/lib/types";
import { AccountBadge } from "./AccountBadge";
import type { AccountType } from "@/lib/types";

interface AccountStatsStripProps {
  byAccount: TradeStats["by_account"];
  selectedAccountId: string;
  onSelect: (accountId: string) => void;
  loading: boolean;
}

function fmt(v: number | null | undefined, decimals = 1): string {
  if (v === null || v === undefined) return "--";
  return v.toFixed(decimals);
}

export function AccountStatsStrip({ byAccount, selectedAccountId, onSelect, loading }: AccountStatsStripProps) {
  const entries = Object.entries(byAccount ?? {});
  if (entries.length === 0 && !loading) return null;

  const dim = loading ? "opacity-50" : "";

  return (
    <div className={`bg-card border border-border rounded overflow-hidden mb-3 ${dim}`}>
      {entries.map(([accountId, data]) => {
        const isSelected = selectedAccountId === accountId;
        const winRateColor = data.win_rate === null
          ? "text-text-muted"
          : data.win_rate >= 50
            ? "text-bull"
            : "text-bear";
        const pnlColorClass = data.total_pnl_usd === 0
          ? "text-text-muted"
          : data.total_pnl_usd > 0
            ? "text-bull"
            : "text-bear";

        return (
          <div
            key={accountId}
            onClick={() => onSelect(isSelected ? "" : accountId)}
            data-interactive
            className={`px-4 py-2 text-sm cursor-pointer hover:bg-elevated flex items-center justify-between gap-3 border-l-2 ${
              isSelected ? "border-l-bull bg-surface-raised" : "border-l-transparent"
            }`}
          >
            <div className="flex items-center gap-2 min-w-0">
              <AccountBadge
                name={data.account_name}
                accountType={data.account_type as AccountType}
              />
              <span className="text-xs text-muted-foreground">
                {data.instrument_type === "futures_mnq" ? "Futures" : "Forex"}
              </span>
            </div>
            <div className="flex items-center gap-4 shrink-0 text-xs">
              <span className="text-muted-foreground">{data.total} trades</span>
              <span className={winRateColor}>
                {data.win_rate !== null ? `${fmt(data.win_rate)}%` : "--"}
              </span>
              <span className={`price ${pnlColorClass}`}>
                {data.total_pnl_usd >= 0 ? "+$" : "-$"}{Math.abs(data.total_pnl_usd).toFixed(2)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
