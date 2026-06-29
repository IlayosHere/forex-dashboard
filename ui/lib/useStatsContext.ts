"use client";

import { useState, useEffect, useMemo, useCallback } from "react";

import type { InstrumentType } from "@/lib/types";

export type PresetKey = "7d" | "30d" | "month" | "3m" | "all";

export interface StatsContext {
  instrumentType: InstrumentType | "";
  accountId: string;
  strategy: string;
  preset: PresetKey;
  customFrom: string;
  customTo: string;
  backtestMode: boolean;
}

export interface UseStatsContextResult {
  context: StatsContext;
  setFilter: (key: keyof StatsContext, value: string) => void;
  setBacktestMode: (v: boolean) => void;
  resetFilters: () => void;
  apiFilters: Record<string, string>;
  ribbonText: string;
  isDefault: boolean;
}

const STORAGE_KEY = "stats:context";

const DEFAULTS: StatsContext = {
  instrumentType: "futures",
  accountId: "",
  strategy: "",
  preset: "30d",
  customFrom: "",
  customTo: "",
  backtestMode: false,
};

const PRESET_LABELS: Record<PresetKey, string> = {
  "7d": "Last 7 days",
  "30d": "Last 30 days",
  month: "This month",
  "3m": "Last 3 months",
  all: "All time",
};

const INSTRUMENT_LABELS: Record<string, string> = {
  futures:     "Futures",
  futures_mnq: "MNQ",
  futures_mes: "MES",
  "":          "All instruments",
};

function computePresetDates(preset: PresetKey): { from: string; to: string } {
  const now = new Date();
  const to = now.toISOString().slice(0, 10);
  if (preset === "all") return { from: "", to: "" };
  if (preset === "month") {
    const from = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
    return { from, to };
  }
  const days = preset === "7d" ? 7 : preset === "30d" ? 30 : 90;
  const d = new Date(now);
  d.setDate(d.getDate() - days);
  return { from: d.toISOString().slice(0, 10), to };
}

function loadStored(): StatsContext {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULTS, accountId: localStorage.getItem("stats:lastAccountId") ?? "" };
    return { ...DEFAULTS, ...JSON.parse(raw) as Partial<StatsContext> };
  } catch {
    return { ...DEFAULTS };
  }
}

export function useStatsContext(): UseStatsContextResult {
  const [context, setContext] = useState<StatsContext>(DEFAULTS);

  useEffect(() => {
    setContext(loadStored());
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(context));
        if (context.accountId) localStorage.setItem("stats:lastAccountId", context.accountId);
      } catch { /* ignore */ }
    }, 300);
    return () => clearTimeout(t);
  }, [context]);

  const setFilter = useCallback((key: keyof StatsContext, value: string) => {
    setContext((prev) => {
      const next = { ...prev, [key]: value };
      if (key === "preset") { next.customFrom = ""; next.customTo = ""; }
      if ((key === "customFrom" || key === "customTo") && value) next.preset = "all";
      return next;
    });
  }, []);

  const setBacktestMode = useCallback((v: boolean) => {
    setContext((prev) => ({ ...prev, backtestMode: v }));
  }, []);

  const resetFilters = useCallback(() => setContext({ ...DEFAULTS }), []);

  const apiFilters = useMemo<Record<string, string>>(() => {
    const dates = (context.customFrom || context.customTo)
      ? { from: context.customFrom, to: context.customTo }
      : computePresetDates(context.preset);
    const f: Record<string, string> = {};
    if (context.instrumentType) f.instrument_type = context.instrumentType;
    if (context.strategy) f.strategy = context.strategy;
    if (context.accountId) f.account_id = context.accountId;
    if (dates.from) f.from = dates.from;
    if (dates.to) f.to = dates.to;
    if (context.backtestMode) {
      f.account_type = "backtest";
    } else if (!context.accountId) {
      f.exclude_account_type = "backtest";
    }
    return f;
  }, [context]);

  const isDefault = context.instrumentType === DEFAULTS.instrumentType
    && context.accountId === ""
    && context.strategy === ""
    && context.preset === DEFAULTS.preset
    && !context.customFrom && !context.customTo;

  const ribbonText = useMemo(() => {
    const inst = INSTRUMENT_LABELS[context.instrumentType] ?? "All instruments";
    const acct = context.accountId ? `Account ${context.accountId}` : "All accounts";
    const window = (context.customFrom || context.customTo)
      ? `${context.customFrom || "…"} → ${context.customTo || "…"}`
      : PRESET_LABELS[context.preset];
    return `${inst} · ${acct} · ${window}`;
  }, [context]);

  return { context, setFilter, setBacktestMode, resetFilters, apiFilters, ribbonText, isDefault };
}
