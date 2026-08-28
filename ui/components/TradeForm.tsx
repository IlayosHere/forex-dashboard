"use client";

import { useState, useEffect, useMemo } from "react";

import { Button } from "@/components/ui/button";
import { TradeSetupFields } from "@/components/TradeSetupFields";
import { TradeAssessmentFields } from "@/components/TradeAssessmentFields";
import { IctTradeFields } from "@/components/IctTradeFields";
import { QtTradeFields } from "@/components/QtTradeFields";

import type { Account } from "@/lib/types";

import { TP_TARGET_DETAIL_OPTIONS } from "@/lib/ictConstants";
import { strategies, getInstrumentType, isFutures as isFuturesHelper } from "@/lib/strategies";
import { useAccounts } from "@/lib/useAccounts";

export interface TradeFormData {
  account_id: string;
  signal_id: string | null;
  scenario_id: string | null;
  strategy: string;
  symbol: string;
  direction: string;
  entry_price: string;
  sl_price: string;
  tp_price: string;
  contracts: string;
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
  ict_tp_target_detail: string;
  ict_ifvg_timeframe: string;
  ict_ifvg_bars: number | null;
  ict_smt_present: boolean | null;
  ict_tdo_aligned: boolean | null;
  ict_cisd_present: boolean | null;
  ict_htf_bias: string | null;
  fees: string;
  criteria_met_at_entry: boolean | null;
  qt_fvg_quarter: string;
  qt_entry_quarter: string;
  qt_fvg_date: string;
  qt_fvg_type: string;
  qt_entry_type: string;
  trade_location: string;
  holding_time_minutes: string;
}

interface TradeFormProps {
  initial: TradeFormData;
  onSubmit: (data: TradeFormData) => void;
  onCancel: () => void;
  loading: boolean;
  signalLabel?: string | null;
  /** "backtest" | "live" — restricts the account dropdown to the current journal mode */
  accountTypeMode?: string | null;
}

export function TradeForm({ initial, onSubmit, onCancel, loading, signalLabel, accountTypeMode }: TradeFormProps) {
  const [form, setForm] = useState<TradeFormData>(initial);
  const [errors, setErrors] = useState<Record<string, boolean>>({});
  const { accounts, refetch: refetchAccounts } = useAccounts();

  const strategyInstrumentType = getInstrumentType(form.strategy);
  const isFutures = isFuturesHelper(strategyInstrumentType);
  // instrument_type is always "futures" for futures trades — the symbol (MNQ/MES)
  // carries the contract identity. P&L and lot sizing branch on symbol, not this field.
  const instrumentType: string = isFutures ? "futures" : strategyInstrumentType;
  const isMnqDaily = form.strategy === "mnq-daily";
  const isQtMnq = form.strategy === "qt-mnq";

  const activeAccounts = useMemo(() => accounts.filter((a) => a.status === "active"), [accounts]);

  // Filter accounts to match journal mode (backtest vs live) and strategy instrument type
  const filteredAccounts = useMemo(() => {
    let pool = activeAccounts;
    if (accountTypeMode === "backtest") {
      pool = pool.filter((a) => a.account_type === "backtest");
    } else if (accountTypeMode === "live") {
      pool = pool.filter((a) => a.account_type !== "backtest");
    }
    if (!form.strategy) return pool;
    if (isFutures) return pool.filter((a) => a.instrument_type?.startsWith("futures"));
    return pool.filter((a) => a.instrument_type === strategyInstrumentType);
  }, [activeAccounts, accountTypeMode, form.strategy, strategyInstrumentType, isFutures]);

  // Auto-select when exactly one account qualifies and none is selected yet
  useEffect(() => {
    if (form.account_id || filteredAccounts.length !== 1) return;
    setForm((prev) => ({ ...prev, account_id: filteredAccounts[0].id }));
  }, [filteredAccounts, form.account_id]);

  const selectedAccount = useMemo(
    () => accounts.find((a) => a.id === form.account_id) ?? null,
    [accounts, form.account_id],
  );
  const isBacktest = selectedAccount?.account_type === "backtest";
  const filteredStrategies = useMemo(() => {
    if (selectedAccount) {
      const acctIsFutures = selectedAccount.instrument_type?.startsWith("futures");
      return strategies.filter((s) =>
        acctIsFutures ? isFuturesHelper(s.instrumentType) : s.instrumentType === selectedAccount.instrument_type,
      );
    }
    if (form.strategy) {
      return strategies.filter((s) =>
        isFutures ? isFuturesHelper(s.instrumentType) : s.instrumentType === strategyInstrumentType,
      );
    }
    return strategies;
  }, [selectedAccount, form.strategy, isFutures, strategyInstrumentType]);

  useEffect(() => {
    setForm(initial);
  }, [initial]);

  // Clear account if it no longer matches the filtered list (e.g. strategy changed)
  useEffect(() => {
    if (form.account_id && filteredAccounts.length > 0 && !filteredAccounts.some((a) => a.id === form.account_id)) {
      setForm((prev) => ({ ...prev, account_id: "" }));
    }
  }, [filteredAccounts, form.account_id]);

  // Clear ICT fields when switching away from mnq-daily
  useEffect(() => {
    if (!isMnqDaily) {
      setForm((prev) => ({
        ...prev,
        ict_setup_type: "",
        ict_setup_detail: "",
        ict_tp_target: "",
        ict_tp_target_detail: "",
        ict_ifvg_timeframe: "",
        ict_ifvg_bars: null,
        ict_smt_present: null,
        ict_tdo_aligned: null,
        ict_cisd_present: null,
        ict_htf_bias: null,
      }));
    }
  }, [isMnqDaily]);

  // Clear QT fields when switching away from qt-mnq strategy
  useEffect(() => {
    if (!isQtMnq) {
      setForm((prev) => ({
        ...prev,
        qt_fvg_quarter: "",
        qt_entry_quarter: "",
        qt_fvg_date: "",
        qt_fvg_type: "",
        qt_entry_type: "",
      }));
    }
  }, [isQtMnq]);

  const set = <K extends keyof TradeFormData>(key: K, value: TradeFormData[K]) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleAccountChange = (accountId: string) => {
    set("account_id", accountId);
    const account = accounts.find((a) => a.id === accountId);
    if (account) {
      const currentStrategyMeta = strategies.find((s) => s.slug === form.strategy);
      if (currentStrategyMeta) {
        const stratIsFutures = isFuturesHelper(currentStrategyMeta.instrumentType);
        const acctIsFutures = account.instrument_type?.startsWith("futures");
        const mismatch = stratIsFutures !== !!acctIsFutures;
        if (mismatch) {
          set("strategy", "");
          set("symbol", "");
        }
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
    if (!isBacktest) {
      const lotNum = Number(form.contracts);
      if (!form.contracts || !isFinite(lotNum) || lotNum <= 0) errs.contracts = true;
    }
    if (form.tp_price) {
      const tpNum = Number(form.tp_price);
      if (!isFinite(tpNum) || tpNum <= 0) errs.tp_price = true;
    }
    if (!form.open_time) errs.open_time = true;
    if (isMnqDaily) {
      if (!form.ict_setup_type) errs.ict_setup_type = true;
      if (form.ict_setup_type && form.ict_setup_type !== "other" && !form.ict_setup_detail) errs.ict_setup_detail = true;
      if (!form.ict_tp_target) errs.ict_tp_target = true;
      const tpTargetDetailRequired = (TP_TARGET_DETAIL_OPTIONS[form.ict_tp_target] ?? []).length > 0;
      if (tpTargetDetailRequired && !form.ict_tp_target_detail) errs.ict_tp_target_detail = true;
      if (!form.ict_ifvg_timeframe) errs.ict_ifvg_timeframe = true;
      if (form.ict_smt_present === null || form.ict_smt_present === undefined) errs.ict_smt_present = true;
      if (form.ict_tdo_aligned === null || form.ict_tdo_aligned === undefined) errs.ict_tdo_aligned = true;
      if (form.ict_cisd_present === null || form.ict_cisd_present === undefined) errs.ict_cisd_present = true;
    }
    if (isQtMnq) {
      if (!form.qt_fvg_quarter) errs.qt_fvg_quarter = true;
      if (!form.qt_entry_quarter) errs.qt_entry_quarter = true;
      if (!form.qt_fvg_type) errs.qt_fvg_type = true;
      if (!form.qt_entry_type) errs.qt_entry_type = true;
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validate()) {
      onSubmit({ ...form, instrument_type: instrumentType, contracts: isBacktest ? "1" : form.contracts });
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
        isBacktest={isBacktest}
        signalLabel={signalLabel}
        onChange={set}
        onAccountChange={handleAccountChange}
        onAccountCreated={handleAccountCreated}
      />

      {isMnqDaily && (
        <IctTradeFields form={form} errors={errors} onChange={set} />
      )}

      {isQtMnq && (
        <QtTradeFields form={form} errors={errors} onChange={set} />
      )}

      <TradeAssessmentFields
        form={form}
        onChange={set}
        isBacktest={selectedAccount?.account_type === "backtest"}
      />

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
