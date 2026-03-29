import { useRouter } from "next/navigation";

import { AccountBadge } from "@/components/AccountBadge";

import type { Trade, AccountType } from "@/lib/types";

interface TradeInfoPanelProps {
  trade: Trade;
  accountType: AccountType;
  unitLabel: string;
  sizeLabel: string;
}

function formatTime(iso: string | null): string {
  if (!iso) return "\u2014";
  try {
    const d = new Date(iso);
    const pad = (n: number) => n.toString().padStart(2, "0");
    return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
  } catch {
    return "\u2014";
  }
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
            className={`text-sm font-semibold px-1.5 py-0.5 rounded ${
              isBuy ? "text-bull bg-bull/10" : "text-bear bg-bear/10"
            }`}
          >
            {isBuy ? "\u25B2" : "\u25BC"} {trade.direction}
          </span>
        </div>
        <div className="text-text-muted text-xs flex items-center gap-2">
          <span>{trade.strategy} &middot; {formatTime(trade.open_time)}</span>
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
