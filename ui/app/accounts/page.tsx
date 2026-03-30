"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { Dialog as DialogPrimitive } from "@base-ui/react/dialog";

import { Button } from "@/components/ui/button";
import { AccountFormFields } from "@/components/AccountFormFields";
import { AccountCard } from "@/components/AccountCard";

import type { Account, AccountType, AccountStatus, InstrumentType } from "@/lib/types";

import { useAccounts } from "@/lib/useAccounts";
import { useTradeStats } from "@/lib/useTradeStats";
import { createAccount, updateAccount, deleteAccount } from "@/lib/api";

interface FormState {
  name: string;
  account_type: AccountType;
  instrument_type: InstrumentType;
  status: AccountStatus;
  prop_firm: string;
  phase: string;
  balance: string;
}

const instrumentTabs: { value: InstrumentType; label: string }[] = [
  { value: "forex", label: "Forex" },
  { value: "futures_mnq", label: "MNQ" },
];

function makeEmptyForm(instrumentType: InstrumentType): FormState {
  return {
    name: "",
    account_type: "demo",
    instrument_type: instrumentType,
    status: "active",
    prop_firm: "",
    phase: "",
    balance: "",
  };
}

interface AccountFormDialogProps {
  open: boolean;
  editingId: string | null;
  form: FormState;
  saving: boolean;
  onChange: <K extends keyof FormState>(key: K, value: FormState[K]) => void;
  onSave: () => void;
  onCancel: () => void;
}

function AccountFormDialog({
  open,
  editingId,
  form,
  saving,
  onChange,
  onSave,
  onCancel,
}: AccountFormDialogProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={(o) => { if (!o) onCancel(); }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Backdrop className="fixed inset-0 z-50 bg-black/50 data-open:animate-in data-open:fade-in-0 data-closed:animate-out data-closed:fade-out-0" />
        <DialogPrimitive.Popup className="fixed z-50 left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[420px] max-w-[95vw] bg-[#111111] border border-[#2a2a2a] rounded-lg shadow-xl outline-hidden p-4 space-y-4 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95">
          <DialogPrimitive.Title className="text-sm font-semibold text-text-primary">
            {editingId ? "Edit Account" : "New Account"}
          </DialogPrimitive.Title>
          <AccountFormFields
            form={form}
            editingId={editingId}
            saving={saving}
            onChange={onChange}
            onSave={onSave}
            onCancel={onCancel}
          />
        </DialogPrimitive.Popup>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

export default function AccountsPage() {
  const [activeTab, setActiveTab] = useState<InstrumentType>("forex");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormState>(makeEmptyForm("forex"));
  const [saving, setSaving] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const { accounts, refetch } = useAccounts();
  const { stats } = useTradeStats({ instrument_type: activeTab });

  const scopedAccounts = useMemo(
    () => accounts.filter((a) => a.instrument_type === activeTab),
    [accounts, activeTab],
  );

  const activeAccounts = useMemo(
    () => scopedAccounts.filter((a) => a.status === "active"),
    [scopedAccounts],
  );

  const inactiveAccounts = useMemo(
    () => scopedAccounts.filter((a) => a.status !== "active"),
    [scopedAccounts],
  );

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const resetForm = () => {
    setForm(makeEmptyForm(activeTab));
    setEditingId(null);
    setShowForm(false);
  };

  const startNew = () => {
    setForm(makeEmptyForm(activeTab));
    setEditingId(null);
    setShowForm(true);
  };

  const startEdit = (account: Account) => {
    setEditingId(account.id);
    setForm({
      name: account.name,
      account_type: account.account_type,
      instrument_type: account.instrument_type,
      status: account.status,
      prop_firm: account.prop_firm ?? "",
      phase: account.phase ?? "",
      balance: account.balance != null ? String(account.balance) : "",
    });
    setShowForm(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    const isFunded = form.account_type === "funded";
    try {
      if (editingId) {
        await updateAccount(editingId, {
          name: form.name,
          status: form.status,
          prop_firm: isFunded ? (form.prop_firm || null) : null,
          phase: isFunded ? (form.phase || null) : null,
          balance: form.balance ? parseFloat(form.balance) : null,
        });
      } else {
        await createAccount({
          name: form.name,
          account_type: form.account_type,
          instrument_type: form.instrument_type,
          status: form.status,
          prop_firm: isFunded ? (form.prop_firm || null) : null,
          phase: isFunded ? (form.phase || null) : null,
          balance: form.balance ? parseFloat(form.balance) : null,
        });
      }
      await refetch();
      resetForm();
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to save account");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    setSaving(true);
    try {
      await deleteAccount(id);
      await refetch();
      setConfirmDeleteId(null);
    } catch (e) {
      alert(e instanceof Error ? e.message : "Failed to delete account");
    } finally {
      setSaving(false);
    }
  };

  const handleTabChange = (tab: InstrumentType) => {
    setActiveTab(tab);
    resetForm();
    setForm(makeEmptyForm(tab));
  };

  function getAccountStats(accountId: string) {
    const byAccount = stats?.by_account;
    if (!byAccount || !(accountId in byAccount)) return undefined;
    const s = byAccount[accountId];
    return {
      trade_count: s.total,
      win_rate: s.win_rate,
      pnl_usd: s.total_pnl_usd,
    };
  }

  return (
    <div className="p-6 max-w-5xl">
      <Link
        href="/"
        className="text-xs text-[#777777] hover:text-[#e0e0e0] transition-colors inline-flex items-center gap-1 mb-3"
      >
        ← Dashboard
      </Link>

      <div className="flex items-center justify-between mb-4">
        <h1 className="text-lg font-semibold text-[#e0e0e0]">Accounts</h1>
        <Button onClick={startNew}>+ New Account</Button>
      </div>

      <div className="flex gap-0 mb-4 border-b border-[#2a2a2a]">
        {instrumentTabs.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => handleTabChange(tab.value)}
            className={`px-4 py-2 text-sm font-medium transition-colors cursor-pointer -mb-px ${
              activeTab === tab.value
                ? "text-[#26a69a] border-b-2 border-[#26a69a]"
                : "text-[#777777] hover:text-[#e0e0e0] border-b-2 border-transparent"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {scopedAccounts.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-[#777777] text-sm mb-3">No accounts yet.</p>
          <Button onClick={startNew}>+ New Account</Button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-4 mt-4">
            {activeAccounts.map((account) => (
              <AccountCard
                key={account.id}
                account={account}
                stats={getAccountStats(account.id)}
                confirmingDelete={confirmDeleteId === account.id}
                saving={saving}
                onEdit={startEdit}
                onDeleteRequest={setConfirmDeleteId}
                onDeleteConfirm={handleDelete}
                onDeleteCancel={() => setConfirmDeleteId(null)}
              />
            ))}
          </div>

          {inactiveAccounts.length > 0 && (
            <>
              <div className="mt-6 mb-2">
                <span className="label">Inactive</span>
              </div>
              <div className="grid grid-cols-2 gap-4 mt-2">
                {inactiveAccounts.map((account) => (
                  <div key={account.id} className="opacity-50">
                    <AccountCard
                      account={account}
                      stats={getAccountStats(account.id)}
                      confirmingDelete={confirmDeleteId === account.id}
                      saving={saving}
                      onEdit={startEdit}
                      onDeleteRequest={setConfirmDeleteId}
                      onDeleteConfirm={handleDelete}
                      onDeleteCancel={() => setConfirmDeleteId(null)}
                    />
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}

      <AccountFormDialog
        open={showForm}
        editingId={editingId}
        form={form}
        saving={saving}
        onChange={set}
        onSave={handleSave}
        onCancel={resetForm}
      />
    </div>
  );
}
