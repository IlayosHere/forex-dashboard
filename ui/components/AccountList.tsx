import { AccountRow } from "@/components/AccountRow";

import type { Account } from "@/lib/types";

interface AccountListProps {
  activeAccounts: Account[];
  inactiveAccounts: Account[];
  totalCount: number;
  confirmDeleteId: string | null;
  saving: boolean;
  onEdit: (account: Account) => void;
  onDeleteRequest: (id: string | null) => void;
  onDeleteConfirm: (id: string) => void;
}

export function AccountList({
  activeAccounts,
  inactiveAccounts,
  totalCount,
  confirmDeleteId,
  saving,
  onEdit,
  onDeleteRequest,
  onDeleteConfirm,
}: AccountListProps) {
  return (
    <div className="flex-1 overflow-y-auto">
      {activeAccounts.length > 0 && (
        <div className="divide-y divide-border">
          {activeAccounts.map((a) => (
            <AccountRow
              key={a.id}
              account={a}
              confirmingDelete={confirmDeleteId === a.id}
              saving={saving}
              onEdit={onEdit}
              onDeleteRequest={onDeleteRequest}
              onDeleteConfirm={onDeleteConfirm}
              onDeleteCancel={() => onDeleteRequest(null)}
            />
          ))}
        </div>
      )}

      {inactiveAccounts.length > 0 && (
        <>
          <div className="px-4 pt-3 pb-1">
            <span className="label">Inactive</span>
          </div>
          <div className="divide-y divide-border">
            {inactiveAccounts.map((a) => (
              <AccountRow
                key={a.id}
                account={a}
                dimmed
                confirmingDelete={confirmDeleteId === a.id}
                saving={saving}
                onEdit={onEdit}
                onDeleteRequest={onDeleteRequest}
                onDeleteConfirm={onDeleteConfirm}
                onDeleteCancel={() => onDeleteRequest(null)}
              />
            ))}
          </div>
        </>
      )}

      {totalCount === 0 && (
        <div className="px-4 py-6 text-center text-sm text-text-muted">
          No accounts yet.
        </div>
      )}
    </div>
  );
}
