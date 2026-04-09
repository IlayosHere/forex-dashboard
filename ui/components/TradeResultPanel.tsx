import { StatusBadge } from "@/components/StatusBadge";

import type { Trade } from "@/lib/types";
import { pnlColor } from "@/lib/format";

interface TradeResultPanelProps {
  trade: Trade;
  unitLabel: string;
}

function formatDuration(open: string, close: string | null): string {
  if (!close) {
    const mins = Math.floor((Date.now() - new Date(open).getTime()) / 60000);
    if (mins < 60) return `${mins}m (running)`;
    const hrs = Math.floor(mins / 60);
    return `${hrs}h ${mins % 60}m (running)`;
  }
  const mins = Math.floor((new Date(close).getTime() - new Date(open).getTime()) / 60000);
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  return `${hrs}h ${mins % 60}m`;
}

export function TradeResultPanel({ trade, unitLabel }: TradeResultPanelProps) {
  return (
    <div className="border border-border rounded p-4 space-y-2 bg-card">
      <span className="label">Result</span>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2">
        <div className="flex justify-between items-center">
          <span className="label">Status</span>
          <StatusBadge status={trade.status} outcome={trade.outcome} />
        </div>
        <div className="flex justify-between">
          <span className="label">Duration</span>
          <span className="text-xs text-text-primary">
            {formatDuration(trade.open_time, trade.close_time)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="label">P&L</span>
          <span className="price font-bold" style={{ color: pnlColor(trade.pnl_pips) }}>
            {trade.pnl_pips != null ? `${trade.pnl_pips > 0 ? "+" : ""}${trade.pnl_pips} ${unitLabel}` : "\u2014"}
            {trade.pnl_usd != null && (
              <span className="text-xs ml-2">({trade.pnl_usd >= 0 ? "+$" : "-$"}{Math.abs(trade.pnl_usd).toFixed(2)})</span>
            )}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="label">R:R Achieved</span>
          <span className="price text-text-primary">
            {trade.rr_achieved != null ? `1 : ${trade.rr_achieved.toFixed(2)}` : "\u2014"}
          </span>
        </div>
      </div>
    </div>
  );
}
