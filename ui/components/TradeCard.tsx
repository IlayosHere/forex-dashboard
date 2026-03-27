"use client";

import type { Trade } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";
import { StarRating } from "./StarRating";

interface TradeCardProps {
  trade: Trade;
  onClick: () => void;
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

export function TradeCard({ trade, onClick }: TradeCardProps) {
  const isBuy = trade.direction === "BUY";

  return (
    <div
      onClick={onClick}
      data-interactive
      className="cursor-pointer px-4 py-3 border-l-2 bg-[#161616] hover:bg-[#1a1a1a]"
      style={{ borderLeftColor: isBuy ? "#26a69a" : "#ef5350" }}
    >
      {/* Line 1 */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span style={{ color: isBuy ? "#26a69a" : "#ef5350" }}>
            {isBuy ? "▲" : "▼"}
          </span>
          <span className="font-bold text-[#e0e0e0]">{trade.symbol}</span>
          <span className="text-xs font-medium" style={{ color: isBuy ? "#26a69a" : "#ef5350" }}>
            {trade.direction}
          </span>
          <span className="price text-sm" style={{ color: pnlColor(trade.pnl_pips) }}>
            {pnlSign(trade.pnl_pips)} pips
          </span>
          <span className="price text-sm" style={{ color: pnlColor(trade.pnl_usd) }}>
            {trade.pnl_usd !== null ? `${pnlSign(trade.pnl_usd, 2)}$` : ""}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {trade.rating != null && (
            <StarRating value={trade.rating} onChange={() => {}} size="sm" />
          )}
          <span className="text-xs text-[#777777]">{trade.strategy}</span>
        </div>
      </div>

      {/* Line 2 */}
      <div className="flex items-center gap-2 mt-1">
        <span className="text-xs text-[#777777]">
          {formatTime(trade.open_time)}
          {" → "}
          {trade.close_time ? formatTime(trade.close_time) : "OPEN"}
        </span>
        <StatusBadge status={trade.status} outcome={trade.outcome} />
        {trade.tags.map((tag) => (
          <span
            key={tag}
            className="text-[10px] bg-[#1e1e1e] text-[#777777] rounded px-1.5 py-0.5"
          >
            {tag}
          </span>
        ))}
      </div>
    </div>
  );
}
