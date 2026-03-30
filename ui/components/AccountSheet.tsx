"use client";

import { useState } from "react";

import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetClose } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { AccountFormFields } from "@/components/AccountFormFields";
import { AccountList } from "@/components/AccountList";

import type { Account, AccountType, AccountStatus, InstrumentType } from "@/lib/types";

import { useAccounts } from "@/lib/useAccounts";
import { createAccount, updateAccount, deleteAccount } from "@/lib/api";

interface AccountSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAccountCreated?: (account: Account) => void;
}

interface FormState {
  name: string;
  account_type: AccountType;
  instrument_type: InstrumentType;
  status: AccountStatus;
  prop_firm: string;
  phase: string;
  balance: string;
}

const EMPTY_FORM: FormState = {
  name: "",
  account_type: "demo",
  instrument_type: "forex",
  status: "active",
  prop_firm: "",
  phase: "",
  balance: "",
};

export function AccountSheet({ open, onOpenChange, onAccountCreated }: AccountSheetProps) {
  const { accounts, refetch } = useAccounts();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const isFunded = form.account_type === "funded";
  const activeAccounts = accounts.filter((a) => a.status === "active");
  const inactiveAccounts = accounts.filter((a) => a.status !== "active");

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
    setShowForm(false);
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
        const account = await createAccount({
          name: form.name,
          account_type: form.account_type,
          instrument_type: form.instrument_type,
          status: form.status,
          prop_firm: isFunded ? (form.prop_firm || null) : null,
          phase: isFunded ? (form.phase || null) : null,
          balance: form.balance ? parseFloat(form.balance) : null,
        });
        onAccountCreated?.(account);
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

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Manage Accounts</SheetTitle>
          <SheetClose className="text-text-muted hover:text-text-primary cursor-pointer transition-colors text-lg leading-none">
            x
          </SheetClose>
        </SheetHeader>

        <AccountList
          activeAccounts={activeAccounts}
          inactiveAccounts={inactiveAccounts}
          totalCount={accounts.length}
          confirmDeleteId={confirmDeleteId}
          saving={saving}
          onEdit={startEdit}
          onDeleteRequest={setConfirmDeleteId}
          onDeleteConfirm={handleDelete}
        />

        <div className="border-t border-border p-4 space-y-3">
          {showForm ? (
            <AccountFormFields
              form={form}
              editingId={editingId}
              saving={saving}
              onChange={set}
              onSave={handleSave}
              onCancel={resetForm}
            />
          ) : (
            <Button variant="outline" onClick={() => { resetForm(); setShowForm(true); }} className="w-full">
              + New Account
            </Button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
