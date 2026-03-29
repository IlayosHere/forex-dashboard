"use client";

import type { Trade, AccountType } from "@/lib/types";
import { getUnitLabel, getInstrumentType } from "@/lib/strategies";
import { StatusBadge } from "./StatusBadge";
import { StarRating } from "./StarRating";
import { AccountBadge } from "./AccountBadge";

interface TradeCardProps {
  trade: Trade;
  onClick: () => void;
  accountType?: AccountType;
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso);
    const m = (d.getUTCMonth() + 1).toString().padStart(2, "0");
    const day = d.getUTCDate().toString().padStart(2, "0");
    const hh = d.getUTCHours().toString().padStart(2, "0");
    const mm = d.getUTCMinutes().toString().padStart(2, "0");
    return `${m}-${day} ${hh}:${mm}`;
  } catch {
    return "—";
  }
}

function pnlColor(v: number | null): string {
  if (v === null || v === 0) return "#777777";
  return v > 0 ? "#26a69a" : "#ef5350";
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
            {trade.pnl_usd !== null ? `${pnlSign(trade.pnl_usd, 2)}$` : ""}
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
          {formatTime(trade.open_time)}
          {" → "}
          {trade.close_time ? formatTime(trade.close_time) : "OPEN"}
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
