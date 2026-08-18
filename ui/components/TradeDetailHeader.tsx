import { AccountBadge } from "@/components/AccountBadge";
import { StatusBadge } from "@/components/StatusBadge";

import type { AccountType, Trade } from "@/lib/types";

import { formatDateTime } from "@/lib/dates";

interface TradeDetailHeaderProps {
  trade: Trade;
  accountType: AccountType;
}

export function TradeDetailHeader({ trade, accountType }: TradeDetailHeaderProps) {
  const isBuy = trade.direction === "BUY";

  return (
    <div className="mb-6">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-xl font-bold text-text-primary">{trade.symbol}</span>
        <span className={`text-sm font-semibold px-1.5 py-0.5 rounded ${isBuy ? "text-bull bg-bull/10" : "text-bear bg-bear/10"}`}>
          {isBuy ? "▲" : "▼"} {trade.direction}
        </span>
        <span className="ml-auto">
          <StatusBadge status={trade.status} outcome={trade.outcome} />
        </span>
      </div>
      <div className="text-text-muted text-xs flex items-center gap-2">
        <span>{trade.strategy} &middot; {formatDateTime(trade.open_time)}</span>
        {trade.account_name && <AccountBadge name={trade.account_name} accountType={accountType} />}
      </div>
    </div>
  );
}
