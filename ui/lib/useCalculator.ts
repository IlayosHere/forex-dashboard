"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { postCalculate } from "./api";
import type { Signal, CalculateResponse } from "./types";

const DEBOUNCE_MS = 300;
const LS_BALANCE = "forex_account_balance";
const LS_RISK = "forex_risk_percent";
const DEFAULT_BALANCE = "10000";
const DEFAULT_RISK = "1.0";

function readLS(key: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  return window.localStorage.getItem(key) ?? fallback;
}

function pipSize(symbol: string): number {
  return symbol.toUpperCase().includes("JPY") ? 0.01 : 0.0001;
}

function toPips(price: number, entry: number, symbol: string): string {
  return String(Math.round(Math.abs(price - entry) / pipSize(symbol) * 10) / 10);
}

export interface UseCalculatorResult {
  slPips: string;
  setSlPips: (v: string) => void;
  tpPips: string;
  setTpPips: (v: string) => void;
  accountBalance: string;
  setAccountBalance: (v: string) => void;
  riskPercent: string;
  setRiskPercent: (v: string) => void;
  result: CalculateResponse | null;
  isPending: boolean;
}

export function useCalculator(signal: Signal): UseCalculatorResult {
  const [slPips, setSlPips] = useState(() => toPips(signal.sl, signal.entry, signal.symbol));
  const [tpPips, setTpPips] = useState(() => toPips(signal.tp, signal.entry, signal.symbol));
  const [accountBalance, setAccountBalanceState] = useState(DEFAULT_BALANCE);
  const [riskPercent, setRiskPercentState] = useState(DEFAULT_RISK);
  const [result, setResult] = useState<CalculateResponse | null>(null);
  const [isPending, setIsPending] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const signalIdRef = useRef(signal.id);

  // Hydrate from localStorage on mount
  useEffect(() => {
    setAccountBalanceState(readLS(LS_BALANCE, DEFAULT_BALANCE));
    setRiskPercentState(readLS(LS_RISK, DEFAULT_RISK));
  }, []);

  // Reset pips when signal changes
  useEffect(() => {
    if (signalIdRef.current !== signal.id) {
      signalIdRef.current = signal.id;
      setSlPips(toPips(signal.sl, signal.entry, signal.symbol));
      setTpPips(toPips(signal.tp, signal.entry, signal.symbol));
      setResult(null);
    }
  }, [signal]);

  const setAccountBalance = useCallback((v: string) => {
    setAccountBalanceState(v);
    if (typeof window !== "undefined") window.localStorage.setItem(LS_BALANCE, v);
  }, []);

  const setRiskPercent = useCallback((v: string) => {
    setRiskPercentState(v);
    if (typeof window !== "undefined") window.localStorage.setItem(LS_RISK, v);
  }, []);

  // Debounced calculate
  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setIsPending(true);

    timerRef.current = setTimeout(async () => {
      try {
        const slNum = parseFloat(slPips);
        const tpNum = parseFloat(tpPips);
        const balNum = parseFloat(accountBalance);
        const riskNum = parseFloat(riskPercent);

        if (
          isNaN(slNum) || isNaN(balNum) || isNaN(riskNum) ||
          balNum <= 0 || riskNum <= 0
        ) {
          setResult(null);
          setIsPending(false);
          return;
        }

        const data = await postCalculate({
          symbol: signal.symbol,
          entry: signal.entry,
          sl_pips: slNum,
          tp_pips: isNaN(tpNum) ? undefined : tpNum,
          account_balance: balNum,
          risk_percent: riskNum,
        });
        setResult(data);
      } catch {
        setResult(null);
      } finally {
        setIsPending(false);
      }
    }, DEBOUNCE_MS);

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [slPips, tpPips, accountBalance, riskPercent, signal.symbol, signal.entry]);

  return {
    slPips, setSlPips,
    tpPips, setTpPips,
    accountBalance, setAccountBalance,
    riskPercent, setRiskPercent,
    result,
    isPending,
  };
}
