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
    <div className={`bg-[#161616] border border-[#2a2a2a] rounded overflow-hidden mb-3 ${dim}`}>
      {entries.map(([accountId, data]) => {
        const isSelected = selectedAccountId === accountId;
        const winRateColor = data.win_rate === null
          ? "#777777"
          : data.win_rate >= 50
            ? "#26a69a"
            : "#ef5350";
        const pnlColor = data.total_pnl_usd === 0
          ? "#777777"
          : data.total_pnl_usd > 0
            ? "#26a69a"
            : "#ef5350";

        return (
          <div
            key={accountId}
            onClick={() => onSelect(isSelected ? "" : accountId)}
            data-interactive
            className={`px-4 py-2 text-sm cursor-pointer hover:bg-[#1e1e1e] flex items-center justify-between gap-3 border-l-2 ${
              isSelected ? "border-l-[#26a69a] bg-[#1a1a1a]" : "border-l-transparent"
            }`}
          >
            <div className="flex items-center gap-2 min-w-0">
              <AccountBadge
                name={data.account_name}
                accountType={data.account_type as AccountType}
              />
              <span className="text-xs text-[#777777]">
                {data.instrument_type === "futures_mnq" ? "Futures" : "Forex"}
              </span>
            </div>
            <div className="flex items-center gap-4 shrink-0 text-xs">
              <span className="text-[#777777]">{data.total} trades</span>
              <span style={{ color: winRateColor }}>
                {data.win_rate !== null ? `${fmt(data.win_rate)}%` : "--"}
              </span>
              <span className="price" style={{ color: pnlColor }}>
                {data.total_pnl_usd >= 0 ? "+" : ""}${fmt(data.total_pnl_usd, 2)}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
