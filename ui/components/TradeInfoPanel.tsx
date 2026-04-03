import { useRouter } from "next/navigation";

import { AccountBadge } from "@/components/AccountBadge";
import { formatDateTime } from "@/lib/dates";

import type { Trade, AccountType } from "@/lib/types";

interface TradeInfoPanelProps {
  trade: Trade;
  accountType: AccountType;
  unitLabel: string;
  sizeLabel: string;
}

export function TradeInfoPanel({ trade, accountType, unitLabel, sizeLabel }: TradeInfoPanelProps) {
  const router = useRouter();
  const isBuy = trade.direction === "BUY";

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xl font-bold text-text-primary">{trade.symbol}</span>
          <span
            className="text-sm font-semibold px-1.5 py-0.5 rounded"
            style={{
              color: isBuy ? "#26a69a" : "#ef5350",
              backgroundColor: isBuy ? "#26a69a1a" : "#ef53501a",
            }}
          >
            {isBuy ? "\u25B2" : "\u25BC"} {trade.direction}
          </span>
        </div>
        <div className="text-text-muted text-xs flex items-center gap-2">
          <span>{trade.strategy} &middot; {formatDateTime(trade.open_time)} UTC</span>
          {trade.account_name && (
            <AccountBadge name={trade.account_name} accountType={accountType} />
          )}
        </div>
      </div>

      {/* Prices */}
      <div className="border border-border rounded p-3 space-y-2 bg-card">
        <div className="flex justify-between">
          <span className="label">Entry</span>
          <span className="price text-text-primary">{trade.entry_price}</span>
        </div>
        <div className="flex justify-between">
          <span className="label">SL</span>
          <span className="price text-text-primary">{trade.sl_price}</span>
        </div>
        {trade.tp_price != null && (
          <div className="flex justify-between">
            <span className="label">TP</span>
            <span className="price text-text-primary">{trade.tp_price}</span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="label">{sizeLabel === "contracts" ? "Contracts" : "Lot Size"}</span>
          <span className="price text-text-primary">{trade.lot_size}</span>
        </div>
        <div className="flex justify-between">
          <span className="label">Risk</span>
          <span className="price text-text-primary">{trade.risk_pips} {unitLabel}</span>
        </div>
      </div>

      {/* Linked signal */}
      {trade.signal_id && (
        <div className="border border-border rounded p-3 bg-card">
          <span className="label">Linked Signal</span>
          <button
            onClick={() => router.push(`/strategy/${trade.strategy}?signal=${trade.signal_id}`)}
            className="block text-xs text-bull hover:underline mt-1 cursor-pointer transition-colors"
          >
            View original signal &rarr;
          </button>
        </div>
      )}
    </div>
  );
}
