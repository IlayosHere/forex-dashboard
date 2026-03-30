import { Button } from "@/components/ui/button";

import type { Account, AccountStatus } from "@/lib/types";

interface AccountCardStats {
  trade_count: number;
  win_rate: number | null;
  pnl_usd: number | null;
}

interface AccountCardProps {
  account: Account;
  stats?: AccountCardStats;
  confirmingDelete: boolean;
  saving: boolean;
  onEdit: (account: Account) => void;
  onDeleteRequest: (id: string) => void;
  onDeleteConfirm: (id: string) => void;
  onDeleteCancel: () => void;
}

const STATUS_COLORS: Record<AccountStatus, string> = {
  active: "bg-bull/10 text-bull",
  passed: "bg-accent-gold/10 text-accent-gold",
  failed: "bg-bear/10 text-bear",
  closed: "bg-surface-input text-text-dim",
};

function formatPnl(pnl: number): string {
  return pnl >= 0 ? `+$${pnl.toLocaleString()}` : `-$${Math.abs(pnl).toLocaleString()}`;
}

export function AccountCard({
  account,
  stats,
  confirmingDelete,
  saving,
  onEdit,
  onDeleteRequest,
  onDeleteConfirm,
  onDeleteCancel,
}: AccountCardProps) {
  const instrumentLabel = account.instrument_type === "futures_mnq" ? "Futures (MNQ)" : "Forex";

  return (
    <div className="bg-card border border-border rounded p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-text-primary truncate">{account.name}</span>
            <span className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded ${STATUS_COLORS[account.status]}`}>
              {account.status}
            </span>
          </div>
          <div className="text-[11px] text-text-muted mt-0.5">
            {account.account_type} &middot; {instrumentLabel}
            {account.prop_firm && ` \u00B7 ${account.prop_firm}`}
            {account.phase && ` \u00B7 ${account.phase}`}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {confirmingDelete ? (
            <>
              <Button
                variant="destructive"
                size="xs"
                onClick={() => onDeleteConfirm(account.id)}
                disabled={saving}
              >
                Yes
              </Button>
              <Button
                variant="outline"
                size="xs"
                onClick={onDeleteCancel}
              >
                No
              </Button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="text-[11px] text-text-muted hover:text-text-primary cursor-pointer transition-colors px-1"
                onClick={() => onEdit(account)}
              >
                Edit
              </button>
              <button
                type="button"
                className="text-[11px] text-text-muted hover:text-bear cursor-pointer transition-colors px-1"
                onClick={() => onDeleteRequest(account.id)}
              >
                Del
              </button>
            </>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-3 text-[12px]">
        <div>
          <span className="text-[11px] text-text-muted">Balance</span>
          <div className="text-[12px] text-text-primary">
            {account.balance != null ? `$${account.balance.toLocaleString()}` : "—"}
          </div>
        </div>
        <div>
          <span className="text-[11px] text-text-muted">Trades</span>
          <div className="text-[12px] text-text-primary">{stats?.trade_count ?? "—"}</div>
        </div>
        <div>
          <span className="text-[11px] text-text-muted">Win Rate</span>
          <div className="text-[12px] text-text-primary">
            {stats?.win_rate != null ? `${Math.round(stats.win_rate * 100)}%` : "—"}
          </div>
        </div>
        <div className="col-span-2">
          <span className="text-[11px] text-text-muted">P&amp;L</span>
          <div
            className="text-[12px]"
            style={
              stats?.pnl_usd != null
                ? { color: stats.pnl_usd >= 0 ? "#26a69a" : "#ef5350" }
                : undefined
            }
          >
            {stats?.pnl_usd != null ? formatPnl(stats.pnl_usd) : "—"}
          </div>
        </div>
      </div>
    </div>
  );
}
