"use client";

import { useState, useEffect, useMemo } from "react";

import { Button } from "@/components/ui/button";
import { TradeSetupFields } from "@/components/TradeSetupFields";
import { TradeAssessmentFields } from "@/components/TradeAssessmentFields";
import { IctTradeFields } from "@/components/IctTradeFields";

import type { Account } from "@/lib/types";

import { useAccounts } from "@/lib/useAccounts";
import { strategies, getInstrumentType } from "@/lib/strategies";

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
  open_time: string;
  tags: string[];
  notes: string;
  rating: number | null;
  confidence: number | null;
  screenshot_url: string;
  instrument_type?: string;
  ict_setup_type: string;
  ict_setup_detail: string;
  ict_tp_target: string;
  ict_ifvg_timeframe: string;
  ict_ifvg_bars: number | null;
  ict_smt_present: boolean | null;
  ict_tdo_aligned: boolean | null;
  ict_htf_bias: string | null;
  fees: string;
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
  const isFutures = instrumentType === "futures_mnq";

  const activeAccounts = useMemo(() => accounts.filter((a) => a.status === "active"), [accounts]);

  // Filter accounts to match the selected strategy's instrument type
  const filteredAccounts = useMemo(() => {
    if (!form.strategy) return activeAccounts;
    return activeAccounts.filter((a) => a.instrument_type === instrumentType);
  }, [activeAccounts, form.strategy, instrumentType]);

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

  // Clear account if it no longer matches the filtered list (e.g. strategy changed)
  useEffect(() => {
    if (form.account_id && filteredAccounts.length > 0 && !filteredAccounts.some((a) => a.id === form.account_id)) {
      setForm((prev) => ({ ...prev, account_id: "" }));
    }
  }, [filteredAccounts, form.account_id]);

  // Clear ICT fields when switching away from a futures strategy
  useEffect(() => {
    if (!isFutures) {
      setForm((prev) => ({
        ...prev,
        ict_setup_type: "",
        ict_setup_detail: "",
        ict_tp_target: "",
        ict_ifvg_timeframe: "",
        ict_ifvg_bars: null,
        ict_smt_present: null,
        ict_tdo_aligned: null,
        ict_htf_bias: null,
      }));
    }
  }, [isFutures]);

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
    const entryNum = Number(form.entry_price);
    if (!form.entry_price || !isFinite(entryNum) || entryNum <= 0) errs.entry_price = true;
    const slNum = Number(form.sl_price);
    if (!form.sl_price || !isFinite(slNum) || slNum <= 0) errs.sl_price = true;
    const lotNum = Number(form.lot_size);
    if (!form.lot_size || !isFinite(lotNum) || lotNum <= 0) errs.lot_size = true;
    if (form.tp_price) {
      const tpNum = Number(form.tp_price);
      if (!isFinite(tpNum) || tpNum <= 0) errs.tp_price = true;
    }
    if (!form.open_time) errs.open_time = true;
    if (isFutures) {
      if (!form.ict_setup_type) errs.ict_setup_type = true;
      if (form.ict_setup_type && form.ict_setup_type !== "other" && !form.ict_setup_detail) errs.ict_setup_detail = true;
      if (!form.ict_tp_target) errs.ict_tp_target = true;
      if (!form.ict_ifvg_timeframe) errs.ict_ifvg_timeframe = true;
      if (form.ict_smt_present === null || form.ict_smt_present === undefined) errs.ict_smt_present = true;
      if (form.ict_tdo_aligned === null || form.ict_tdo_aligned === undefined) errs.ict_tdo_aligned = true;
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      onSubmit({ ...form, instrument_type: instrumentType });
    } else {
      setTimeout(() => {
        const el = document.querySelector(".border-bear");
        if (el) (el as HTMLElement).scrollIntoView({ behavior: "smooth", block: "center" });
      }, 0);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-xl">
      <TradeSetupFields
        form={form}
        errors={errors}
        activeAccounts={filteredAccounts}
        filteredStrategies={filteredStrategies}
        isFutures={isFutures}
        signalLabel={signalLabel}
        onChange={set}
        onAccountChange={handleAccountChange}
        onAccountCreated={handleAccountCreated}
      />

      {isFutures && (
        <IctTradeFields form={form} errors={errors} onChange={set} />
      )}

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
