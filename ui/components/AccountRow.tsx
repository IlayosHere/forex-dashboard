import { Button } from "@/components/ui/button";

import type { Account, AccountStatus } from "@/lib/types";

interface AccountRowProps {
  account: Account;
  dimmed?: boolean;
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

export function AccountRow({
  account,
  dimmed = false,
  confirmingDelete,
  saving,
  onEdit,
  onDeleteRequest,
  onDeleteConfirm,
  onDeleteCancel,
}: AccountRowProps) {
  return (
    <div className={`px-4 py-2.5 flex items-center justify-between gap-2 ${dimmed ? "opacity-50" : ""}`}>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-text-primary truncate">{account.name}</span>
          <span className={`text-[10px] font-medium uppercase px-1.5 py-0.5 rounded ${STATUS_COLORS[account.status]}`}>
            {account.status}
          </span>
        </div>
        <div className="text-[11px] text-text-muted mt-0.5">
          {account.account_type} &middot; {account.instrument_type === "futures_mnq" ? "Futures (MNQ)" : "Forex"}
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
  );
}
