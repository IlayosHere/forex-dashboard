import { StatusBadge } from "@/components/StatusBadge";

import type { Trade, BeOutcome } from "@/lib/types";

import { pnlColor } from "@/lib/format";

const BE_OUTCOME_LABEL: Record<BeOutcome, { label: string; cls: string }> = {
  prevented_loss: { label: "Prevented Loss", cls: "text-bull" },
  missed_tp:      { label: "Missed TP",      cls: "text-bear" },
};

interface TradeResultPanelProps {
  trade: Trade;
  unitLabel: string;
  isBacktest?: boolean;
}


export function TradeResultPanel({ trade, unitLabel, isBacktest = false }: TradeResultPanelProps) {
  return (
    <div className="border border-border rounded p-4 space-y-2 bg-card">
      <span className="label">Result</span>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-2">
        <div className="flex justify-between items-center">
          <span className="label">Status</span>
          <StatusBadge status={trade.status} outcome={trade.outcome} />
        </div>
        {isBacktest ? (
          <div className="flex justify-between">
            <span className="label">R</span>
            <span className="price font-bold" style={{ color: pnlColor(trade.rr_achieved) }}>
              {trade.rr_achieved != null ? `${trade.rr_achieved >= 0 ? "+" : ""}${trade.rr_achieved.toFixed(2)}R` : "\u2014"}
            </span>
          </div>
        ) : (
          <>
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
          </>
        )}
        {!isBacktest && trade.fees != null && (
          <div className="flex justify-between">
            <span className="label">Broker Fees</span>
            <span className="price text-text-muted">-${trade.fees.toFixed(2)}</span>
          </div>
        )}
        {trade.outcome === "breakeven" && (
          <div className="flex justify-between items-center">
            <span className="label">BE Outcome</span>
            {trade.be_outcome ? (
              <span className={`text-xs font-medium ${BE_OUTCOME_LABEL[trade.be_outcome].cls}`}>
                {BE_OUTCOME_LABEL[trade.be_outcome].label}
              </span>
            ) : (
              <span className="text-xs text-text-muted italic">Not reviewed</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
