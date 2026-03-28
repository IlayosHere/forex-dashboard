"use client";

import { useState, useEffect, useMemo } from "react";

import { Button } from "@/components/ui/button";
import { TradeSetupFields } from "@/components/TradeSetupFields";
import { TradeAssessmentFields } from "@/components/TradeAssessmentFields";

import type { Account } from "@/lib/types";

import { useAccounts } from "@/lib/useAccounts";
import { strategies, getInstrumentType, getUnitLabel, getSizeLabel } from "@/lib/strategies";

export interface TradeFormData {
  account_id: string;
  signal_id: string | null;
  strategy: string;
  symbol: string;
  direction: string;
  entry_price: string;
  sl_price: string;
  tp_price: string;
  lot_size: string;
  risk_pips: string;
  open_time: string;
  tags: string[];
  notes: string;
  rating: number | null;
  confidence: number | null;
  screenshot_url: string;
  instrument_type?: string;
}

interface TradeFormProps {
  initial: TradeFormData;
  onSubmit: (data: TradeFormData) => void;
  onCancel: () => void;
  loading: boolean;
  signalLabel?: string | null;
}

export function TradeForm({ initial, onSubmit, onCancel, loading, signalLabel }: TradeFormProps) {
  const [form, setForm] = useState<TradeFormData>(initial);
  const [errors, setErrors] = useState<Record<string, boolean>>({});
  const { accounts, refetch: refetchAccounts } = useAccounts();

  const instrumentType = getInstrumentType(form.strategy);
  const unitLabel = getUnitLabel(instrumentType);
  const sizeLabel = getSizeLabel(instrumentType);
  const isFutures = instrumentType === "futures_mnq";

  const activeAccounts = useMemo(() => accounts.filter((a) => a.status === "active"), [accounts]);

  const selectedAccount = useMemo(
    () => accounts.find((a) => a.id === form.account_id) ?? null,
    [accounts, form.account_id],
  );
  const filteredStrategies = useMemo(() => {
    if (!selectedAccount) return strategies;
    return strategies.filter((s) => s.instrumentType === selectedAccount.instrument_type);
  }, [selectedAccount]);

  useEffect(() => {
    setForm(initial);
  }, [initial]);

  const set = <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleAccountChange = (accountId: string) => {
    set("account_id", accountId);
    const account = accounts.find((a) => a.id === accountId);
    if (account) {
      const currentStrategyMeta = strategies.find((s) => s.slug === form.strategy);
      if (currentStrategyMeta && currentStrategyMeta.instrumentType !== account.instrument_type) {
        set("strategy", "");
        set("symbol", "");
      }
    }
  };

  const handleAccountCreated = (account: Account) => {
    refetchAccounts();
    set("account_id", account.id);
  };

  const validate = (): boolean => {
    const errs: Record<string, boolean> = {};
    if (!form.account_id) errs.account_id = true;
    if (!form.strategy) errs.strategy = true;
    if (!form.symbol) errs.symbol = true;
    if (!form.direction) errs.direction = true;
    if (!form.entry_price || isNaN(Number(form.entry_price))) errs.entry_price = true;
    if (!form.sl_price || isNaN(Number(form.sl_price))) errs.sl_price = true;
    if (!form.lot_size || isNaN(Number(form.lot_size))) errs.lot_size = true;
    if (!form.open_time) errs.open_time = true;
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) onSubmit({ ...form, instrument_type: instrumentType });
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-xl">
      <TradeSetupFields
        form={form}
        errors={errors}
        activeAccounts={activeAccounts}
        filteredStrategies={filteredStrategies}
        isFutures={isFutures}
        unitLabel={unitLabel}
        signalLabel={signalLabel}
        onChange={set}
        onAccountChange={handleAccountChange}
        onAccountCreated={handleAccountCreated}
      />

      <TradeAssessmentFields form={form} onChange={set} />

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="outline" onClick={onCancel} disabled={loading}>
          Cancel
        </Button>
        <Button type="submit" disabled={loading}>
          {loading ? "Saving..." : "Save Trade"}
        </Button>
      </div>
    </form>
  );
}
