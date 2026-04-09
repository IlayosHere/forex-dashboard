"use client";

import type { Trade, AccountType } from "@/lib/types";
import { getUnitLabel, getInstrumentType } from "@/lib/strategies";
import { StatusBadge } from "./StatusBadge";
import { StarRating } from "./StarRating";
import { AccountBadge } from "./AccountBadge";
import { formatShortDate } from "@/lib/dates";
import { pnlColor } from "@/lib/format";

interface TradeCardProps {
  trade: Trade;
  onClick: () => void;
  accountType?: AccountType;
}

function pnlSign(v: number | null, decimals = 1): string {
  if (v === null) return "—";
  const prefix = v > 0 ? "+" : "";
  return `${prefix}${v.toFixed(decimals)}`;
}

export function TradeCard({ trade, onClick, accountType }: TradeCardProps) {
  const isBuy = trade.direction === "BUY";
  const unitLabel = getUnitLabel(trade.instrument_type ?? getInstrumentType(trade.strategy));

  return (
    <div
      onClick={onClick}
      data-interactive
      className={`cursor-pointer px-4 py-3 border-l-2 bg-card hover:bg-surface-raised ${
        isBuy ? "border-l-bull" : "border-l-bear"
      }`}
    >
      {/* Line 1 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={isBuy ? "text-bull" : "text-bear"}>
            {isBuy ? "▲" : "▼"}
          </span>
          <span className="font-bold text-foreground">{trade.symbol}</span>
          <span className={`text-xs font-medium ${isBuy ? "text-bull" : "text-bear"}`}>
            {trade.direction}
          </span>
          <span className="price text-sm" style={{ color: pnlColor(trade.pnl_pips) }}>
            {pnlSign(trade.pnl_pips)} {unitLabel}
          </span>
          <span className="price text-sm" style={{ color: pnlColor(trade.pnl_usd) }}>
            {trade.pnl_usd !== null ? `${trade.pnl_usd >= 0 ? "+$" : "-$"}${Math.abs(trade.pnl_usd).toFixed(2)}` : ""}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {trade.rating != null && (
            <StarRating value={trade.rating} onChange={() => {}} size="sm" />
          )}
          <span className="text-xs text-muted-foreground">{trade.strategy}</span>
        </div>
      </div>

      {/* Line 2 */}
      <div className="flex items-center gap-2 mt-1">
        <span className="text-xs text-muted-foreground">
          {formatShortDate(trade.open_time)}
          {" → "}
          {trade.close_time ? formatShortDate(trade.close_time) : "OPEN"}
        </span>
        {trade.account_name && (
          <AccountBadge
            name={trade.account_name}
            accountType={accountType ?? "demo"}
          />
        )}
        <StatusBadge status={trade.status} outcome={trade.outcome} />
        {trade.tags.map((tag) => (
          <span
            key={tag}
            className="text-[10px] bg-elevated text-muted-foreground rounded px-1.5 py-0.5"
          >
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}
